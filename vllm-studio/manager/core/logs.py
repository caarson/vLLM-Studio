from __future__ import annotations

import asyncio

from fastapi import WebSocket
from loguru import logger

from .docker_ctl import DockerController


async def stream_container_logs(websocket: WebSocket, docker_ctl: DockerController, name: str) -> None:
    await websocket.accept()
    try:
        generator = docker_ctl.stream_logs(name)
        for chunk in generator:
            await websocket.send_text(chunk.decode(errors="ignore"))
            await asyncio.sleep(0)
    except Exception as exc:
        logger.warning("Log stream error for {}: {}", name, exc)
        await websocket.close(code=1011)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
