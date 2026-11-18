import json
import time
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_runtime
from app.clients.ollama import (
    ModelNotFound,
    OllamaError,
    RuntimeProtocolError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.clients.protocol import RuntimeClient
from app.models.openai import (
    OpenAIChatChoice,
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIModel,
    OpenAIModelList,
)

openai_router = APIRouter(prefix="/v1", tags=["OpenAI-compatible API"])


@openai_router.get(
    "/models",
    response_model=OpenAIModelList,
    summary="List models in OpenAI-compatible format",
)
async def list_openai_models(
    runtime: RuntimeClient = Depends(get_runtime),
) -> OpenAIModelList:
    created = int(time.time())
    models = await runtime.list_models()
    return OpenAIModelList(
        data=[OpenAIModel(id=model.name, created=created) for model in models]
    )


@openai_router.post(
    "/chat/completions",
    response_model=OpenAIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Create an OpenAI-compatible chat completion",
    description=(
        "Returns a JSON completion by default. Set `stream` to true to receive "
        "OpenAI-compatible server-sent event chunks."
    ),
)
async def create_chat_completion(
    body: OpenAIChatRequest,
    runtime: RuntimeClient = Depends(get_runtime),
) -> OpenAIChatResponse | StreamingResponse:
    completion_id = f"chatcmpl-{uuid4().hex}"
    created = int(time.time())

    if not body.stream:
        response = await runtime.chat(
            model=body.model,
            messages=body.messages,
            temperature=body.temperature,
        )
        return OpenAIChatResponse(
            id=completion_id,
            created=created,
            model=response.model,
            choices=[OpenAIChatChoice(message=response.message)],
        )

    content_stream = runtime.chat_stream(
        model=body.model,
        messages=body.messages,
        temperature=body.temperature,
    )
    try:
        first_content = await anext(content_stream)
    except StopAsyncIteration:
        await content_stream.aclose()
        raise RuntimeProtocolError("The model runtime returned an empty stream.")

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield _event(
                _chunk(
                    completion_id,
                    created,
                    body.model,
                    delta={"role": "assistant"},
                )
            )
            yield _event(
                _chunk(
                    completion_id,
                    created,
                    body.model,
                    delta={"content": first_content},
                )
            )
            async for content in content_stream:
                yield _event(
                    _chunk(
                        completion_id,
                        created,
                        body.model,
                        delta={"content": content},
                    )
                )
            yield _event(
                _chunk(
                    completion_id,
                    created,
                    body.model,
                    delta={},
                    finish_reason="stop",
                )
            )
        except OllamaError as exception:
            yield _event({"error": _openai_stream_error(exception)})
        finally:
            await content_stream.aclose()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _chunk(
    completion_id: str,
    created: int,
    model: str,
    *,
    delta: dict[str, str],
    finish_reason: str | None = None,
) -> dict[str, object]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }


def _event(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}\n\n"


def _openai_stream_error(exception: OllamaError) -> dict[str, str]:
    if isinstance(exception, ModelNotFound):
        code, message, error_type = (
            "model_not_found",
            "The requested model is not available.",
            "invalid_request_error",
        )
    elif isinstance(exception, RuntimeTimeout):
        code, message, error_type = (
            "runtime_timeout",
            "The model runtime request timed out.",
            "server_error",
        )
    elif isinstance(exception, RuntimeUnavailable):
        code, message, error_type = (
            "runtime_unavailable",
            "The model runtime is unavailable.",
            "server_error",
        )
    else:
        code, message, error_type = (
            "runtime_error",
            "The model runtime request failed.",
            "server_error",
        )
    return {"message": message, "type": error_type, "code": code}
