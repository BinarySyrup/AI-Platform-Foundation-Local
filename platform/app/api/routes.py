from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_runtime, get_settings
from app.clients.protocol import RuntimeClient
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    ModelListResponse,
)
from app.settings import Settings

router = APIRouter()


@router.get("/", response_class=HTMLResponse, tags=["root"])
async def root(request: Request) -> HTMLResponse:
    build_version = escape(request.app.version)
    return HTMLResponse(
        "<html><body><h1>AI Platform Foundation - API</h1>"
        f"<div>API Version:{build_version}</div></body></html>"
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/api/v1/models",
    response_model=ModelListResponse,
    responses={503: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["models"],
)
async def list_models(
    runtime: Annotated[RuntimeClient, Depends(get_runtime)],
) -> ModelListResponse:
    return ModelListResponse(models=await runtime.list_models())


@router.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    tags=["chat"],
)
async def chat(
    body: ChatRequest,
    runtime: Annotated[RuntimeClient, Depends(get_runtime)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    model = body.model or settings.default_model
    return await runtime.chat(
        model=model,
        messages=body.messages,
        temperature=body.options.temperature,
    )
