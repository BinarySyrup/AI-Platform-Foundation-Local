import pytest
from app.clients.ollama import (
    ModelNotFound,
    RuntimeProtocolError,
    RuntimeResponseError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.main import create_app
from app.models.schemas import ChatMessage, ChatResponse, ModelSummary
from app.settings import Settings
from fastapi import FastAPI
from tests.helpers import send_request


class FakeRuntime:
    def __init__(self, chat_error: Exception | None = None) -> None:
        self.chat_error = chat_error
        self.chat_call: dict[str, object] | None = None
        self.model_list_calls = 0
        self.models = [ModelSummary(name="qwen2.5:1.5b")]

    async def list_models(self) -> list[ModelSummary]:
        self.model_list_calls += 1
        return self.models

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
    ) -> ChatResponse:
        self.chat_call = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.chat_error is not None:
            raise self.chat_error
        return ChatResponse(
            model=model,
            message=ChatMessage(
                role="assistant",
                content="Use infrastructure as code.",
            ),
        )


def make_app(runtime: FakeRuntime) -> FastAPI:
    settings = Settings(default_model="qwen2.5:1.5b")
    return create_app(settings=settings, runtime=runtime)


def test_root_page_displays_current_api_version() -> None:
    app = make_app(FakeRuntime())
    app.version = "2.3.4"

    response = send_request(app, "GET", "/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == (
        "<html><body><h1>AI Platform Foundation - API</h1>"
        "<div>API Version:2.3.4</div></body></html>"
    )


def test_health_is_liveness_only_and_returns_request_id() -> None:
    runtime = FakeRuntime()
    response = send_request(make_app(runtime), "GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]
    assert runtime.model_list_calls == 0
    assert runtime.chat_call is None


def test_model_list_is_normalized() -> None:
    response = send_request(make_app(FakeRuntime()), "GET", "/api/v1/models")

    assert response.status_code == 200
    assert response.json() == {"models": [{"name": "qwen2.5:1.5b"}]}


def test_chat_uses_default_model_and_normalizes_response() -> None:
    runtime = FakeRuntime()
    body = {
        "messages": [{"role": "user", "content": "Explain IaC."}],
        "options": {"temperature": 0.2},
    }
    response = send_request(
        make_app(runtime),
        "POST",
        "/api/v1/chat",
        json_body=body,
    )

    assert response.status_code == 200
    assert response.json() == {
        "model": "qwen2.5:1.5b",
        "message": {
            "role": "assistant",
            "content": "Use infrastructure as code.",
        },
    }
    assert runtime.chat_call == {
        "model": "qwen2.5:1.5b",
        "messages": [ChatMessage(role="user", content="Explain IaC.")],
        "temperature": 0.2,
    }


def test_chat_honors_an_explicit_model_override() -> None:
    runtime = FakeRuntime()
    response = send_request(
        make_app(runtime),
        "POST",
        "/api/v1/chat",
        json_body={
            "model": "custom:tag",
            "messages": [{"role": "user", "content": "Hello."}],
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "custom:tag"
    assert runtime.chat_call is not None
    assert runtime.chat_call["model"] == "custom:tag"


@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (ModelNotFound(), 404, "model_not_found"),
        (RuntimeUnavailable(), 503, "runtime_unavailable"),
        (RuntimeTimeout(), 504, "runtime_timeout"),
        (RuntimeResponseError(), 502, "runtime_error"),
        (RuntimeProtocolError(), 502, "runtime_error"),
    ],
)
def test_runtime_errors_use_documented_error_envelope(
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    response = send_request(
        make_app(FakeRuntime(chat_error=error)),
        "POST",
        "/api/v1/chat",
        json_body={"messages": [{"role": "user", "content": "Hello."}]},
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_invalid_request_is_normalized_without_echoing_input() -> None:
    secret_prompt = "do not echo this invalid prompt"
    response = send_request(
        make_app(FakeRuntime()),
        "POST",
        "/api/v1/chat",
        json_body={
            "messages": [{"role": "user", "content": secret_prompt}],
            "options": {"temperature": 3},
            "unexpected": "field",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert secret_prompt not in response.text


def test_runtime_errors_do_not_expose_upstream_details() -> None:
    runtime = FakeRuntime(chat_error=RuntimeUnavailable("private upstream detail"))
    response = send_request(
        make_app(runtime),
        "POST",
        "/api/v1/chat",
        json_body={"messages": [{"role": "user", "content": "Hello."}]},
    )

    assert response.status_code == 503
    assert "private upstream detail" not in response.text
