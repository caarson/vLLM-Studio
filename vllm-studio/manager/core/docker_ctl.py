from __future__ import annotations

import os
import re
import time
from typing import Dict, Iterable, Optional

import docker
from docker.errors import NotFound
from docker.models.containers import Container
from docker.types import DeviceRequest
from loguru import logger

from .models import ModelStatus, RuntimeStatus


def _compose_project() -> str:
    return os.environ.get("COMPOSE_PROJECT_NAME", "vllm-studio")


def _network_name() -> str:
    return f"{_compose_project()}_default"


class DockerController:
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.image = os.environ.get("VLLM_IMAGE", "vllm/vllm-openai:latest")
        self.cache_volume = os.environ.get("HF_CACHE_VOLUME", "vllm-studio-hf-cache")
        self.cache_dir = os.environ.get("CACHE_DIR", "/hf-cache")

    def _container_name(self, name: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", name)
        return f"vllm-{safe}"

    def _find_container(self, name: str) -> Optional[Container]:
        container_name = self._container_name(name)
        try:
            return self.client.containers.get(container_name)
        except NotFound:
            return None

    def build_command(self, repo: str, flags: Dict[str, object]) -> Iterable[str]:
        command = [
            "python",
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            repo,
        ]
        for key, value in flags.items():
            if value in (None, "", [], {}):
                continue
            cli_key = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    command.append(cli_key)
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    command.append(cli_key)
                    command.append(str(item))
                continue
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    command.append(cli_key)
                    command.append(f"{sub_key}:{sub_val}")
                continue
            command.append(cli_key)
            command.append(str(value))
        return command

    def start_vllm_container(
        self,
        *,
        name: str,
        repo: str,
        flags: Dict[str, object],
        port: int,
        gpu_index: int,
    ) -> RuntimeStatus:
        container_name = self._container_name(name)
        existing = self._find_container(name)
        if existing is not None:
            logger.info("Stopping existing container {}", container_name)
            existing.remove(force=True)
        command_flags = dict(flags)
        command_flags.setdefault("host", "0.0.0.0")
        command_flags.setdefault("port", port)
        command_flags.setdefault("download_dir", self.cache_dir)
        environment = {}
        if token := os.environ.get("HUGGINGFACE_HUB_TOKEN"):
            environment["HUGGINGFACE_HUB_TOKEN"] = token
        ports = {f"{port}/tcp": port}
        device_requests = []
        if gpu_index is not None:
            device_requests.append(
                DeviceRequest(
                    count=1,
                    capabilities=[["gpu"]],
                    device_ids=[str(gpu_index)],
                )
            )
        kwargs = {
            "image": self.image,
            "name": container_name,
            "command": self.build_command(repo, command_flags),
            "environment": environment,
            "detach": True,
            "device_requests": device_requests or None,
            "volumes": {self.cache_volume: {"bind": self.cache_dir, "mode": "rw"}},
            "ports": ports,
        }
        try:
            kwargs["network"] = _network_name()
        except Exception:
            pass
        container = self.client.containers.create(**kwargs)
        container.start()
        logger.info("Started container {} on port {}", container_name, port)
        return RuntimeStatus(
            status=ModelStatus.starting,
            port=port,
            gpu=gpu_index,
            container_id=container.id,
        )

    def stop_vllm_container(self, name: str) -> None:
        container = self._find_container(name)
        if container is None:
            return
        logger.info("Stopping container {}", container.name)
        container.remove(force=True)

    def get_status(self, name: str) -> Optional[RuntimeStatus]:
        container = self._find_container(name)
        if container is None:
            return None
        container.reload()
        state = container.attrs.get("State", {})
        status = state.get("Status")
        health_raw = (state.get("Health") or {}).get("Status")
        health = "ready" if health_raw == "healthy" else health_raw
        if status == "running":
            model_status = ModelStatus.running
        elif status == "exited":
            model_status = ModelStatus.error
        else:
            model_status = ModelStatus.starting
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        port = None
        if ports:
            for key, value in ports.items():
                if value and isinstance(value, list):
                    port = int(value[0].get("HostPort"))
                    break
        gpu = None
        if container.attrs.get("HostConfig", {}).get("DeviceRequests"):
            device_requests = container.attrs["HostConfig"]["DeviceRequests"]
            if device_requests and device_requests[0].get("DeviceIDs"):
                gpu = int(device_requests[0]["DeviceIDs"][0])
        return RuntimeStatus(
            status=model_status,
            port=port,
            gpu=gpu,
            container_id=container.id,
            health=health,
        )

    def wait_for_health(self, name: str, timeout: float) -> RuntimeStatus:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_status(name)
            if status and status.health == "healthy":
                return RuntimeStatus(
                    status=ModelStatus.running,
                    port=status.port,
                    gpu=status.gpu,
                    container_id=status.container_id,
                    health="ready",
                )
            time.sleep(2)
        raise TimeoutError(f"Timed out waiting for {name} health")

    def stream_logs(self, name: str):
        container = self._find_container(name)
        if container is None:
            raise NotFound(name)
        return container.logs(stream=True, follow=True, tail=100)
