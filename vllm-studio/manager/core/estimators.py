from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple

from loguru import logger

from .hf_utils import RepoFile, total_size_bytes


DTYPE_BYTES = {
    "float32": 4,
    "float16": 2,
    "bfloat16": 2,
    "auto": 2,
}


def disk_requirements(files: list[RepoFile], cache_dir: Path) -> Tuple[float, float]:
    total = total_size_bytes(files)
    usage = shutil.disk_usage(cache_dir)
    return total / (1024**3), usage.free / (1024**3)


def _safe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def estimate_params(config: Dict) -> int:
    hidden = _safe_int(config.get("hidden_size"), 0)
    layers = _safe_int(config.get("num_hidden_layers"), 0)
    intermediate = _safe_int(config.get("intermediate_size"), hidden * 4)
    vocab = _safe_int(config.get("vocab_size"), hidden * 2)
    if hidden == 0 or layers == 0:
        size = _safe_int(config.get("model_size_in_billions"), 0)
        if size:
            return int(size * 1e9)
        return 0
    params = (hidden * intermediate * layers * 2) + (hidden * vocab)
    return params


def gpu_memory_free_gb() -> float:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        values = [float(x.strip()) / 1024 for x in result.stdout.strip().splitlines() if x.strip()]
        return max(values) if values else 0.0
    except Exception as exc:
        logger.debug("Failed to query GPU memory: {}", exc)
        return 0.0


def estimate_vram(
    *,
    config: Dict,
    dtype: str,
    max_model_len: int,
    tensor_parallel_size: int,
    gpu_memory_utilization: float,
) -> float:
    params = estimate_params(config)
    if params == 0:
        # Fallback heuristic: 1.6x disk size (in bytes) assuming dtype 16bit
        params = _safe_int(config.get("model_size_in_billions"), 7) * int(1e9)
    bytes_per_param = DTYPE_BYTES.get(dtype, 2)
    base = params * bytes_per_param
    kv_overhead = params * 0.1 + max_model_len * bytes_per_param * tensor_parallel_size
    total = (base + kv_overhead) * 1.2
    total /= tensor_parallel_size or 1
    total /= gpu_memory_utilization or 1
    return total / (1024**3)
