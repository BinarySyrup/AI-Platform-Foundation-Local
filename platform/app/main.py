import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.clients.ollama import (
    ModelNotFound,
    OllamaClient,
    OllamaError,
    RuntimeProtocolError,
    RuntimeResponseError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.clients.protocol import RuntimeClient
from app.models.schemas import (
    ErrorDetail,
    ErrorResponse,
    ValidationIssue,
)
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
) -> FastAPI:
    app_settings = settings or Settings()
    logger.setLevel(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if runtime is not None:
            application.state.runtime = runtime
            yield
            return

        async with httpx.AsyncClient(
            base_url=str(app_settings.ollama_base_url).rstrip("/"),
            timeout=httpx.Timeout(app_settings.request_timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        ) as http_client:
            application.state.runtime = OllamaClient(http_client)
            yield

    application = FastAPI(
        title="Local AI Platform API",
        description="A local API for model discovery and non-streaming chat.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.include_router(router)

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
