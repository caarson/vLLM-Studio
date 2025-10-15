from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Dict, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from loguru import logger

from core.catalog import Catalog
from core.docker_ctl import DockerController
from core.logs import stream_container_logs
from core.models import (
    ModelCreateRequest,
    ModelEntry,
    ModelResponse,
    ModelStatus,
    ProgressPhase,
    RouteRequest,
    RuntimeStatus,
    SettingsUpdateRequest,
    StartRequest,
    StopRequest,
)
from core.progress import ProgressRegistry
from core.settings_groups import GROUPS, settings_index
from core.router import proxy_openai

APP_HOME = Path(os.environ.get("APP_HOME", Path(__file__).resolve().parent))
DATA_DIR = APP_HOME / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = Path(os.environ.get("CACHE_DIR", "/hf-cache"))
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    pass
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'catalog.db'}")
MANAGER_TOKEN = os.environ.get("MANAGER_TOKEN")
UI_ORIGINS = [origin.strip() for origin in os.environ.get("UI_ORIGIN", "http://localhost:5173,http://localhost:4000").split(",") if origin.strip()]

catalog = Catalog(DATABASE_URL, CACHE_DIR)
docker_ctl = DockerController()
progress_registry = ProgressRegistry(CACHE_DIR)
http_bearer = HTTPBearer(auto_error=False)
runtime_state: Dict[str, RuntimeStatus] = {}

app = FastAPI(title="vLLM Studio Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=UI_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


async def require_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> None:
    if MANAGER_TOKEN is None:
        return
    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != MANAGER_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_entry_or_404(name: str) -> ModelEntry:
    entry = catalog.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return entry


@app.get("/api/models", response_model=list[ModelResponse])
async def list_models() -> list[ModelResponse]:
    items = catalog.list_models(runtime_state)
    return [ModelResponse(**item) for item in items]


@app.post("/api/models", dependencies=[Depends(require_token)], status_code=201)
async def add_model(payload: ModelCreateRequest):
    if catalog.get(payload.name):
        raise HTTPException(status_code=409, detail="Model already exists")
    flags = payload.flags or {}
    flags.setdefault("model", payload.repo)
    flags.setdefault("download_dir", str(CACHE_DIR))
    entry = catalog.add(
        name=payload.name,
        repo=payload.repo,
        revision=payload.revision,
        default_port=payload.default_port,
        default_gpu=payload.default_gpu,
        flags=flags,
    )
    runtime_state.pop(payload.name, None)
    return JSONResponse(status_code=201, content={"name": entry.name})


@app.delete("/api/models/{name}", dependencies=[Depends(require_token)])
async def delete_model(name: str):
    status = runtime_state.get(name)
    if status and status.status == ModelStatus.running:
        raise HTTPException(status_code=400, detail="Stop the model before deleting")
    catalog.delete(name)
    runtime_state.pop(name, None)
    return {"deleted": name}


async def wait_for_ready(name: str, port: int, timeout: float = 480.0) -> None:
    url = f"http://localhost:{port}/health"
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(timeout=10.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    runtime = runtime_state.get(name)
                    if runtime:
                        runtime_state[name] = RuntimeStatus(
                            status=ModelStatus.running,
                            port=runtime.port,
                            gpu=runtime.gpu,
                            container_id=runtime.container_id,
                            health="ready",
                        )
                    return
            except Exception:
                await asyncio.sleep(2)
                continue
            await asyncio.sleep(2)
    raise HTTPException(status_code=504, detail="Timed out waiting for model to become ready")


@app.post("/api/start", dependencies=[Depends(require_token)])
async def start_model(payload: StartRequest):
    entry = get_entry_or_404(payload.name)
    status = runtime_state.get(entry.name)
    if status and status.status == ModelStatus.running:
        raise HTTPException(status_code=400, detail="Model already running")
    flags = dict(entry.flags_json)
    port = int(flags.get("port", entry.default_port))
    gpu_index = int(flags.get("default_gpu", entry.default_gpu))
    runtime_state[entry.name] = docker_ctl.start_vllm_container(
        name=entry.name,
        repo=entry.repo,
        flags=flags,
        port=port,
        gpu_index=gpu_index,
    )
    try:
        await wait_for_ready(entry.name, port)
    except Exception as exc:
        logger.error("Model failed to start: {}", exc)
        runtime_state[entry.name] = RuntimeStatus(status=ModelStatus.error)
        raise
    return runtime_state[entry.name]


@app.post("/api/stop", dependencies=[Depends(require_token)])
async def stop_model(payload: StopRequest):
    entry = get_entry_or_404(payload.name)
    docker_ctl.stop_vllm_container(entry.name)
    runtime_state[entry.name] = RuntimeStatus(status=ModelStatus.stopped)
    return {"stopped": entry.name}


@app.post("/api/route", dependencies=[Depends(require_token)])
async def route_model(payload: RouteRequest):
    entry = get_entry_or_404(payload.name)
    status = runtime_state.get(entry.name)
    if not status or status.status != ModelStatus.running:
        raise HTTPException(status_code=400, detail="Model not running")
    catalog.set_active(entry.name)
    return {"active": entry.name}


@app.post("/api/restart", dependencies=[Depends(require_token)])
async def restart_model(payload: StartRequest):
    await stop_model(StopRequest(name=payload.name))
    return await start_model(payload)


@app.get("/api/settings/{name}")
async def get_settings(name: str):
    entry = get_entry_or_404(name)
    values = dict(entry.flags_json)
    for group in GROUPS:
        for field in group["fields"]:
            if field.key not in values:
                values[field.key] = field.default
    response = []
    for group in GROUPS:
        group_fields = []
        for field in group["fields"]:
            group_fields.append(
                {
                    "key": field.key,
                    "type": field.field_type,
                    "value": values.get(field.key, field.default),
                    "default": field.default,
                    "description": field.description,
                    "choices": field.choices,
                }
            )
        response.append({"group": group["group"], "fields": group_fields})
    return response


@app.put("/api/settings/{name}", dependencies=[Depends(require_token)])
async def update_settings(name: str, payload: SettingsUpdateRequest):
    entry = get_entry_or_404(name)
    allowed = settings_index()
    updated = dict(entry.flags_json)
    for key, value in payload.values.items():
        if key not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown flag {key}")
        updated[key] = value
    catalog.update_flags(name, updated)
    return {"updated": name}


@app.get("/api/progress/{name}")
async def progress(name: str):
    entry = get_entry_or_404(name)
    runtime = runtime_state.get(name, RuntimeStatus(status=ModelStatus.stopped))
    health = runtime.health
    snapshot = progress_registry.snapshot(entry, runtime.status, health)
    return snapshot


@app.websocket("/api/logs/stream/{name}")
async def logs_stream(websocket: WebSocket, name: str):
    await stream_container_logs(websocket, docker_ctl, name)


async def proxy_request(request: Request, path: str):
    active = catalog.get_active()
    if not active:
        raise HTTPException(status_code=400, detail="No active model")
    runtime = runtime_state.get(active)
    if not runtime or runtime.status != ModelStatus.running or not runtime.port:
        raise HTTPException(status_code=502, detail="Active model unavailable")
    url = f"http://localhost:{runtime.port}/{path}"
    return await proxy_openai(request, url)


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def openai_proxy(path: str, request: Request):
    return await proxy_request(request, f"v1/{path}")


@app.on_event("startup")
async def initial_sync():
    items = catalog.list_models({})
    for item in items:
        runtime_state[item["name"]] = docker_ctl.get_status(item["name"]) or RuntimeStatus(status=ModelStatus.stopped)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def serve_ui(full_path: str):
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": "UI not built"})
