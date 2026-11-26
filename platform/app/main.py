import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.openai_routes import openai_router
from app.api.rag_routes import rag_router
from app.api.routes import router
from app.clients.docling import DoclingClient
from app.clients.ollama import (
    ModelNotFound,
    OllamaClient,
    OllamaError,
    RuntimeProtocolError,
    RuntimeResponseError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.clients.protocol import EmbeddingClient, RuntimeClient
from app.clients.qdrant import QdrantClient
from app.models.schemas import (
    ErrorDetail,
    ErrorResponse,
    ValidationIssue,
)
from app.rag.errors import RagError
from app.rag.service import RagService
from app.settings import Settings

logger = logging.getLogger("ai_platform")


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    if request.url.path.startswith("/v1/"):
        error_type = "invalid_request_error" if status_code < 500 else "server_error"
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "message": message,
                    "type": error_type,
                    "code": code,
                }
            },
            headers={"X-Request-ID": request_id},
        )
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers={"X-Request-ID": request_id},
    )


def create_app(
    settings: Settings | None = None,
    runtime: RuntimeClient | None = None,
    rag_service: RagService | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    logger.setLevel(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with (
            httpx.AsyncClient(
                base_url=str(app_settings.ollama_base_url).rstrip("/"),
                timeout=httpx.Timeout(app_settings.request_timeout_seconds),
                follow_redirects=False,
                trust_env=False,
            ) as runtime_http_client,
            httpx.AsyncClient(
                base_url=str(app_settings.docling_base_url).rstrip("/"),
                timeout=httpx.Timeout(
                    app_settings.rag_ingestion_timeout_seconds,
                    connect=5.0,
                ),
                follow_redirects=False,
                trust_env=False,
            ) as docling_http_client,
            httpx.AsyncClient(
                base_url=str(app_settings.qdrant_base_url).rstrip("/"),
                timeout=httpx.Timeout(
                    app_settings.request_timeout_seconds,
                    connect=5.0,
                ),
                follow_redirects=False,
                trust_env=False,
            ) as qdrant_http_client,
        ):
            actual_runtime = runtime or OllamaClient(runtime_http_client)
            actual_rag = rag_service or RagService(
                settings=app_settings,
                embeddings=cast(EmbeddingClient, actual_runtime),
                docling=DoclingClient(docling_http_client),
                qdrant=QdrantClient(
                    qdrant_http_client,
                    app_settings.rag_collection_name,
                ),
            )
            application.state.runtime = actual_runtime
            application.state.rag = actual_rag
            readiness_task = None
            if runtime is None or rag_service is not None:
                readiness_task = asyncio.create_task(actual_rag.readiness_loop())
            try:
                yield
            finally:
                if readiness_task is not None:
                    readiness_task.cancel()
                    try:
                        await readiness_task
                    except asyncio.CancelledError:
                        pass

    application = FastAPI(
        title="Local AI Platform API",
        description=(
            "A local platform API with versioned endpoints and an OpenAI-compatible "
            "interface for model discovery and streaming or non-streaming chat."
        ),
        version="1.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "root", "description": "API landing page and version."},
            {"name": "health", "description": "API liveness checks."},
            {"name": "models", "description": "Models available in Ollama."},
            {"name": "chat", "description": "Non-streaming chat completion."},
            {
                "name": "OpenAI-compatible API",
                "description": "Model listing and chat completions for API clients.",
            },
            {
                "name": "RAG",
                "description": "Local PDF ingestion, retrieval, and grounded chat.",
            },
        ],
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.include_router(router)
    application.include_router(openai_router)
    application.include_router(rag_router)

    @application.middleware("http")
    async def add_request_id_and_log(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "request_complete request_id=%s method=%s path=%s "
            "status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        details = [
            ValidationIssue(
                field=".".join(str(part) for part in error["loc"]),
                message=error["msg"],
                kind=error["type"],
            )
            for error in exception.errors()
        ]
        return _error_response(
            request,
            status_code=422,
            code="invalid_request",
            message="Request validation failed.",
            details=details,
        )

    @application.exception_handler(OllamaError)
    async def ollama_error_handler(
        request: Request,
        exception: OllamaError,
    ) -> JSONResponse:
        if isinstance(exception, ModelNotFound):
            status_code, code, message = (
                404,
                "model_not_found",
                "The requested model is not available in Ollama.",
            )
        elif isinstance(exception, RuntimeTimeout):
            status_code, code, message = (
                504,
                "runtime_timeout",
                "The model runtime request timed out.",
            )
        elif isinstance(exception, RuntimeUnavailable):
            status_code, code, message = (
                503,
                "runtime_unavailable",
                "The model runtime is unavailable.",
            )
        elif isinstance(exception, (RuntimeProtocolError, RuntimeResponseError)):
            status_code, code, message = (
                502,
                "runtime_error",
                "The model runtime returned an invalid or unsuccessful response.",
            )
        else:
            status_code, code, message = (
                502,
                "runtime_error",
                "The model runtime request failed.",
            )
        return _error_response(
            request,
            status_code=status_code,
            code=code,
            message=message,
        )

    @application.exception_handler(RagError)
    async def rag_error_handler(
        request: Request,
        exception: RagError,
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=exception.status_code,
            code=exception.code,
            message=exception.message,
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        if exception.status_code == 404:
            code, message = "not_found", "The requested resource was not found."
        elif exception.status_code == 405:
            code, message = "method_not_allowed", "The request method is not allowed."
        else:
            code, message = "http_error", "The request could not be completed."
        return _error_response(
            request,
            status_code=exception.status_code,
            code=code,
            message=message,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exception: Exception,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "unhandled_error request_id=%s error_type=%s",
            request_id,
            type(exception).__name__,
        )
        return _error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    return application


app = create_app()
