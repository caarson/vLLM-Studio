from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from cachetools import TTLCache, cached
from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError
from loguru import logger


@dataclass(frozen=True)
class RepoFile:
    path: str
    size: int
    is_lora: bool = False


api = HfApi(token=os.environ.get("HUGGINGFACE_HUB_TOKEN"))
_cache = TTLCache(maxsize=64, ttl=600)


@cached(_cache)
def fetch_repo_manifest(repo_id: str, revision: Optional[str] = None) -> List[RepoFile]:
    try:
        info = api.repo_info(repo_id, revision=revision, files_metadata=True)
    except RepositoryNotFoundError as exc:
        logger.warning("Repo not found: {}", repo_id)
        raise exc
    files: List[RepoFile] = []
    for sibling in info.siblings:
        size = getattr(sibling, "size", None) or 0
        files.append(RepoFile(path=sibling.rfilename, size=size, is_lora=sibling.rfilename.endswith(".safetensors")))
    return files


def total_size_bytes(files: List[RepoFile]) -> int:
    return sum(file.size for file in files)


@cached(_cache)
def load_model_config(repo_id: str, revision: Optional[str] = None) -> Dict:
    try:
        info = api.model_info(repo_id, revision=revision, files_metadata=True)
    except Exception as exc:
        logger.warning("Unable to load model config: {}", exc)
        return {}
    config = info.config or {}
    if isinstance(config, dict):
        return config
    try:
        return json.loads(config)
    except Exception:
        return {}
