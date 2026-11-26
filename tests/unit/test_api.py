import asyncio
import json

import pytest
from app.clients.ollama import (
    ModelNotFound,
    RuntimeProtocolError,
    RuntimeResponseError,
    RuntimeTimeout,
    RuntimeUnavailable,
)
from app.main import create_app
from app.models.schemas import ChatMessage, ChatResponse, ModelSummary, RAGSource
from app.rag.service import RagPrompt
from app.settings import Settings
from fastapi import FastAPI
from tests.helpers import send_request


class FakeRuntime:
    def __init__(self, chat_error: Exception | None = None) -> None:
        self.chat_error = chat_error
        self.chat_call: dict[str, object] | None = None
        self.stream_call: dict[str, object] | None = None
        self.model_list_calls = 0
        self.models = [ModelSummary(name="llama3.1:8b")]

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

    async def chat_stream(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
    ):
        self.stream_call = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.chat_error is not None:
            raise self.chat_error
        yield "Use infrastructure "
        yield "as code."


class FakeRagService:
    def __init__(self, *, calibrated: bool = True, can_answer: bool = True) -> None:
        self.settings = Settings(
            default_model="llama3.1:8b",
            rag_score_threshold=0.5 if calibrated else None,
        )
        self.ready = True
        self.can_answer = can_answer
        self.sources = [
            RAGSource(
                document_id="doc-a",
                filename="guide.pdf",
                page_number=4,
                score=0.9,
            )
        ]

    async def readiness_loop(self) -> None:
        await asyncio.Event().wait()

    def health(self) -> dict[str, object]:
        return {"status": "ready", "dependencies": {}}

    async def prepare_prompt(self, messages: list[ChatMessage]) -> RagPrompt:
        return RagPrompt(
            messages=[
                ChatMessage(role="system", content="Use retrieved document evidence."),
                *messages,
            ],
            sources=self.sources if self.can_answer else [],
            no_support=not self.can_answer,
        )

    @staticmethod
    def add_citations(answer: str, sources: list[RAGSource]) -> str:
        if not sources:
            return answer
        return f"{answer}\n\nSources:\n- guide.pdf, page 4"


def make_app(
    runtime: FakeRuntime, rag_service: FakeRagService | None = None
) -> FastAPI:
    settings = Settings(default_model="llama3.1:8b")
    return create_app(settings=settings, runtime=runtime, rag_service=rag_service)


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


def test_swagger_ui_and_openapi_schema_are_available() -> None:
    app = make_app(FakeRuntime())

    docs_response = send_request(app, "GET", "/docs")
    schema_response = send_request(app, "GET", "/openapi.json")

    assert docs_response.status_code == 200
    assert "swagger-ui" in docs_response.text.lower()
    assert schema_response.status_code == 200
    assert schema_response.json()["paths"]["/api/v1/chat"]["post"]["summary"] == (
        "Generate a chat response"
    )
    chat_examples = schema_response.json()["paths"]["/api/v1/chat"]["post"][
        "requestBody"
    ]["content"]["application/json"]["examples"]
    assert chat_examples["infrastructure-as-code"]["value"] == {
        "model": "llama3.1:8b",
        "messages": [
            {
                "role": "user",
                "content": "Explain infrastructure as code.",
            }
        ],
        "options": {"temperature": 0},
    }


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
    assert response.json() == {"models": [{"name": "llama3.1:8b"}]}


def test_openai_model_list_returns_runtime_models() -> None:
    response = send_request(make_app(FakeRuntime()), "GET", "/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == "llama3.1:8b"
    assert payload["data"][0]["object"] == "model"


def test_openai_model_list_adds_rag_aliases_when_ready_and_calibrated() -> None:
    runtime = FakeRuntime()
    runtime.models.append(ModelSummary(name="nomic-embed-text:v1.5"))

    response = send_request(
        make_app(runtime, FakeRagService()),
        "GET",
        "/v1/models",
    )

    assert response.status_code == 200
    assert [model["id"] for model in response.json()["data"]] == [
        "llama3.1:8b",
        "llama3.1:8b-rag",
    ]


def test_openai_model_list_hides_rag_aliases_until_threshold_is_calibrated() -> None:
    response = send_request(
        make_app(FakeRuntime(), FakeRagService(calibrated=False)),
        "GET",
        "/v1/models",
    )

    assert response.status_code == 200
    assert [model["id"] for model in response.json()["data"]] == ["llama3.1:8b"]


def test_rag_model_alias_retrieves_context_and_cites_document_page() -> None:
    runtime = FakeRuntime()
    response = send_request(
        make_app(runtime, FakeRagService()),
        "POST",
        "/v1/chat/completions",
        json_body={
            "model": "llama3.1:8b-rag",
            "messages": [{"role": "user", "content": "Who checks the gate?"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "llama3.1:8b-rag"
    assert (
        "Sources:\n- guide.pdf, page 4"
        in response.json()["choices"][0]["message"]["content"]
    )
    assert runtime.chat_call is not None
    assert runtime.chat_call["model"] == "llama3.1:8b"
    assert runtime.chat_call["messages"][0].role == "system"


def test_rag_alias_returns_no_support_without_calling_generation_model() -> None:
    runtime = FakeRuntime()
    response = send_request(
        make_app(runtime, FakeRagService(can_answer=False)),
        "POST",
        "/v1/chat/completions",
        json_body={
            "model": "llama3.1:8b-rag",
            "messages": [{"role": "user", "content": "What is the access code?"}],
        },
    )

    assert response.status_code == 200
    assert (
        "do not provide enough information"
        in response.json()["choices"][0]["message"]["content"]
    )
    assert runtime.chat_call is None


def test_openai_chat_completion_returns_compatible_response() -> None:
    runtime = FakeRuntime()
    response = send_request(
        make_app(runtime),
        "POST",
        "/v1/chat/completions",
        json_body={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "Explain IaC."}],
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["model"] == "llama3.1:8b"
    assert payload["choices"][0]["message"] == {
        "role": "assistant",
        "content": "Use infrastructure as code.",
    }
    assert runtime.chat_call is not None
    assert runtime.chat_call["temperature"] == 0.2


def test_openai_chat_completion_streams_server_sent_events() -> None:
    response = send_request(
        make_app(FakeRuntime()),
        "POST",
        "/v1/chat/completions",
        json_body={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "Explain IaC."}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    chunks = [json.loads(event) for event in events if event != "[DONE]"]
    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert [chunk["choices"][0]["delta"].get("content") for chunk in chunks[1:3]] == [
        "Use infrastructure ",
        "as code.",
    ]
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert events[-1] == "[DONE]"


def test_openai_runtime_errors_use_compatible_error_shape() -> None:
    response = send_request(
        make_app(FakeRuntime(chat_error=RuntimeUnavailable())),
        "POST",
        "/v1/chat/completions",
        json_body={
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": "Hello."}],
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "runtime_unavailable"
    assert response.headers["X-Request-ID"]


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
        "model": "llama3.1:8b",
        "message": {
            "role": "assistant",
            "content": "Use infrastructure as code.",
        },
    }
    assert runtime.chat_call == {
        "model": "llama3.1:8b",
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
