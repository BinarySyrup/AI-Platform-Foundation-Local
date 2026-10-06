from typing import cast

from fastapi import Request

from app.clients.protocol import RuntimeClient
from app.settings import Settings


def get_runtime(request: Request) -> RuntimeClient:
    return cast(RuntimeClient, request.app.state.runtime)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)
