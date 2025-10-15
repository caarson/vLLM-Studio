import os
from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MANAGER_TOKEN"] = "test-token"
os.environ["CACHE_DIR"] = "/tmp/hf-cache-test"

import importlib

app_module = importlib.import_module("app")
app = app_module.app


class FakeDocker:
    def __init__(self) -> None:
        self.started: Dict[str, object] = {}

    def start_vllm_container(self, **kwargs):
        status = app_module.RuntimeStatus(
            status=app_module.ModelStatus.starting,
            port=kwargs.get("port", 8001),
            gpu=kwargs.get("gpu_index", 0),
            container_id=f"fake-{kwargs['name']}",
        )
        self.started[kwargs["name"]] = status
        return status

    def stop_vllm_container(self, name: str):
        self.started[name] = app_module.RuntimeStatus(status=app_module.ModelStatus.stopped)

    def get_status(self, name: str):
        return self.started.get(name)

    def stream_logs(self, name: str):
        yield b"log line"


def fake_wait_for_ready(name: str, port: int, timeout: float = 0.1):
    app_module.runtime_state[name] = app_module.RuntimeStatus(
        status=app_module.ModelStatus.running,
        port=port,
        gpu=0,
        container_id=f"fake-{name}",
        health="ready",
    )


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch) -> Generator[TestClient, None, None]:
    fake_docker = FakeDocker()
    monkeypatch.setattr(app_module, "docker_ctl", fake_docker)
    monkeypatch.setattr(app_module, "wait_for_ready", fake_wait_for_ready)

    def progress_stub(entry, status, health):
        return {
            "phase": "ready",
            "bytes_total": 10,
            "bytes_downloaded": 10,
            "network_mbps_avg": 1.0,
            "eta_seconds": 0,
            "disk_needed_gb": 1.0,
            "disk_free_gb": 100.0,
            "vram_needed_gb": 8.0,
            "vram_free_gb": 24.0,
            "vram_fit": True,
            "files": [],
        }

    monkeypatch.setattr(app_module.progress_registry, "snapshot", progress_stub)

    client = TestClient(app)
    yield client


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_catalog_lifecycle(patch_dependencies):
    client = patch_dependencies
    payload = {
        "name": "llama-8b",
        "repo": "meta-llama/Llama-3.1-8B-Instruct",
    }
    response = client.post("/api/models", json=payload, headers=auth_headers())
    assert response.status_code == 201

    list_response = client.get("/api/models")
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert data[0]["name"] == "llama-8b"


def test_start_stop_route_flow(patch_dependencies):
    client = patch_dependencies
    client.post(
        "/api/models",
        json={"name": "model-a", "repo": "meta/model"},
        headers=auth_headers(),
    )

    start_response = client.post("/api/start", json={"name": "model-a"}, headers=auth_headers())
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    route_response = client.post("/api/route", json={"name": "model-a"}, headers=auth_headers())
    assert route_response.status_code == 200

    progress_response = client.get("/api/progress/model-a")
    assert progress_response.status_code == 200
    assert progress_response.json()["phase"] == "ready"

    stop_response = client.post("/api/stop", json={"name": "model-a"}, headers=auth_headers())
    assert stop_response.status_code == 200


def test_settings_validation(patch_dependencies):
    client = patch_dependencies
    client.post(
        "/api/models",
        json={"name": "model-b", "repo": "meta/model"},
        headers=auth_headers(),
    )

    response = client.put(
        "/api/settings/model-b",
        json={"values": {"unknown_flag": True}},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_proxy_requires_route(patch_dependencies):
    client = patch_dependencies
    response = client.post("/v1/chat/completions", json={"messages": []})
    assert response.status_code == 400
