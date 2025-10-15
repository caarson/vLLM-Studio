from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from loguru import logger

from .estimators import disk_requirements, estimate_vram, gpu_memory_free_gb
from .hf_utils import RepoFile, fetch_repo_manifest
from .models import ModelEntry, ModelStatus, ProgressPhase
from .settings_groups import settings_index


@dataclass
class ThroughputState:
    last_bytes: int
    last_time: float
    ema_bps: float


class ProgressRegistry:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self._throughput: Dict[str, ThroughputState] = {}
        self._settings_index = settings_index()

    def _repo_dir(self, entry: ModelEntry) -> Path:
        return self.cache_dir / entry.repo

    def _collect_downloaded(self, entry: ModelEntry, files: List[RepoFile]) -> Dict[str, int]:
        root = self._repo_dir(entry)
        downloaded: Dict[str, int] = {}
        for file in files:
            local_path = root / file.path
            if local_path.exists():
                try:
                    downloaded[file.path] = local_path.stat().st_size
                except FileNotFoundError:
                    downloaded[file.path] = 0
            else:
                downloaded[file.path] = 0
        return downloaded

    def _update_throughput(self, name: str, bytes_downloaded: int) -> float:
        now = time.time()
        state = self._throughput.get(name)
        if state is None:
            state = ThroughputState(last_bytes=bytes_downloaded, last_time=now, ema_bps=0.0)
            self._throughput[name] = state
            return 0.0
        elapsed = max(now - state.last_time, 1e-3)
        delta = max(bytes_downloaded - state.last_bytes, 0)
        instant = delta / elapsed
        ema = state.ema_bps * 0.7 + instant * 0.3 if state.ema_bps else instant
        state.last_time = now
        state.last_bytes = bytes_downloaded
        state.ema_bps = ema
        return ema

    def snapshot(self, entry: ModelEntry, runtime_status: ModelStatus, health: str | None) -> Dict:
        try:
            manifest = fetch_repo_manifest(entry.repo, entry.revision)
        except Exception as exc:
            logger.warning("Unable to resolve repo manifest: {}", exc)
            manifest = []
        downloaded_map = self._collect_downloaded(entry, manifest) if manifest else {}
        bytes_total = sum(item.size for item in manifest)
        bytes_downloaded = sum(downloaded_map.values())
        bps = self._update_throughput(entry.name, bytes_downloaded)
        disk_needed, disk_free = disk_requirements(manifest, self.cache_dir)
        flags = entry.flags_json or {}
        dtype = flags.get("dtype", "float16")
        max_model_len = int(flags.get("max_model_len", 32768))
        tensor_parallel_size = int(flags.get("tensor_parallel_size", 1))
        gpu_mem_util = float(flags.get("gpu_memory_utilization", 0.9))
        config = {}
        try:
            from .hf_utils import load_model_config

            config = load_model_config(entry.repo, entry.revision)
        except Exception:
            config = {}
        vram_needed = estimate_vram(
            config=config,
            dtype=dtype,
            max_model_len=max_model_len,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=gpu_mem_util,
        )
        vram_free = gpu_memory_free_gb()
        vram_fit = vram_free == 0.0 or vram_free >= vram_needed

        if not manifest:
            phase = ProgressPhase.resolving
        elif bytes_downloaded < bytes_total:
            phase = ProgressPhase.downloading
        elif runtime_status == ModelStatus.running and health != "ready":
            phase = ProgressPhase.loading
        elif runtime_status == ModelStatus.running:
            phase = ProgressPhase.ready
        else:
            phase = ProgressPhase.loading if bytes_downloaded >= bytes_total else ProgressPhase.downloading

        eta_seconds = None
        if bps > 0 and bytes_total > bytes_downloaded:
            eta_seconds = int((bytes_total - bytes_downloaded) / bps)

        files_breakdown: List[Dict] = []
        for file in manifest:
            downloaded = downloaded_map.get(file.path, 0)
            files_breakdown.append(
                {
                    "path": file.path,
                    "size": file.size,
                    "downloaded": downloaded,
                    "complete": downloaded >= file.size and file.size > 0,
                }
            )

        return {
            "phase": phase.value,
            "bytes_total": bytes_total,
            "bytes_downloaded": bytes_downloaded,
            "network_mbps_avg": round(bps / (1024 * 1024), 2) if bps else 0.0,
            "eta_seconds": eta_seconds,
            "disk_needed_gb": round(disk_needed, 2),
            "disk_free_gb": round(disk_free, 2),
            "vram_needed_gb": round(vram_needed, 2),
            "vram_free_gb": round(vram_free, 2),
            "vram_fit": vram_fit,
            "files": files_breakdown,
        }
