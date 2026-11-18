import asyncio
import json
from collections.abc import Callable

import httpx
import pytest
from app.clients.ollama import (
    ModelNotFound,
    OllamaClient,
    RuntimeProtocolError,
    RuntimeResponseError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.models.schemas import ChatMessage


def run_async(operation):
    return asyncio.run(operation)


def make_async_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://ollama:11434",
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )


def test_list_models_returns_only_public_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "llama3.1:8b",
                        "digest": "internal-digest",
                    }
                ]
            },
        )

    async def operation():
        async with make_async_client(handler) as http_client:
            return await OllamaClient(http_client).list_models()

    models = run_async(operation())

    assert [model.name for model in models] == ["llama3.1:8b"]


def test_chat_uses_non_streaming_runtime_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "llama3.1:8b",
                "message": {"role": "assistant", "content": "Hello."},
                "done": True,
            },
        )

    async def operation():
        async with make_async_client(handler) as http_client:
            return await OllamaClient(http_client).chat(
                model="llama3.1:8b",
                messages=[ChatMessage(role="user", content="Hi.")],
                temperature=0.2,
            )

    response = run_async(operation())
    sent = json.loads(requests[0].content)

    assert requests[0].method == "POST"
    assert requests[0].url.path == "/api/chat"
    assert sent == {
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": "Hi."}],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    assert response.message.content == "Hello."


def test_chat_maps_unknown_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    async def operation():
        async with make_async_client(handler) as http_client:
            await OllamaClient(http_client).chat(
                model="missing:model",
                messages=[ChatMessage(role="user", content="Hello.")],
                temperature=None,
            )

    with pytest.raises(ModelNotFound):
        run_async(operation())


def test_chat_stream_uses_streaming_runtime_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            content=(
                b'{"model":"llama3.1:8b","message":{"content":"Hel"},"done":false}\n'
                b'{"model":"llama3.1:8b","message":{"content":"lo."},"done":true}\n'
            ),
        )

    async def operation():
        async with make_async_client(handler) as http_client:
            return [
                chunk
                async for chunk in OllamaClient(http_client).chat_stream(
                    model="llama3.1:8b",
                    messages=[ChatMessage(role="user", content="Hi.")],
                    temperature=0.2,
                )
            ]

    chunks = run_async(operation())
    sent = json.loads(requests[0].content)

    assert chunks == ["Hel", "lo."]
    assert requests[0].url.path == "/api/chat"
    assert sent == {
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": "Hi."}],
        "stream": True,
        "options": {"temperature": 0.2},
    }


def test_chat_stream_maps_runtime_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid request"})

    async def operation():
        async with make_async_client(handler) as http_client:
            return [
                chunk
                async for chunk in OllamaClient(http_client).chat_stream(
                    model="llama3.1:8b",
                    messages=[ChatMessage(role="user", content="Hi.")],
                    temperature=None,
                )
            ]

    with pytest.raises(RuntimeResponseError):
        run_async(operation())


def test_client_maps_timeout_without_leaking_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream detail")

    async def operation():
        async with make_async_client(handler) as http_client:
            await OllamaClient(http_client).list_models()

    with pytest.raises(RuntimeTimeout):
        run_async(operation())


def test_client_maps_connection_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection detail", request=request)

    async def operation():
        async with make_async_client(handler) as http_client:
            await OllamaClient(http_client).list_models()

    with pytest.raises(RuntimeUnavailable):
        run_async(operation())


def test_client_rejects_malformed_runtime_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": []})

    async def operation():
        async with make_async_client(handler) as http_client:
            await OllamaClient(http_client).list_models()

    with pytest.raises(RuntimeProtocolError):
        run_async(operation())
