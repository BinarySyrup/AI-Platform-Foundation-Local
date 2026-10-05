import asyncio
from typing import Any

import httpx
from fastapi import FastAPI


def send_request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    async def perform_request() -> httpx.Response:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, json=json_body)

    return asyncio.run(perform_request())
