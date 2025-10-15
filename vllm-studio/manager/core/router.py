from __future__ import annotations

from typing import AsyncIterator, Dict

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse


async def proxy_openai(request: Request, base_url: str) -> Response:
    headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}
    async with httpx.AsyncClient(timeout=None) as client:
        body = await request.body()
        if request.headers.get("accept") == "text/event-stream":
            upstream = await client.stream(request.method, base_url, headers=headers, content=body)

            async def event_stream() -> AsyncIterator[bytes]:
                async for chunk in upstream.aiter_raw():
                    yield chunk

            return StreamingResponse(event_stream(), media_type="text/event-stream")
        response = await client.request(request.method, base_url, headers=headers, content=body)
        return Response(status_code=response.status_code, content=response.content, headers=dict(response.headers))
