import os
from collections.abc import Iterator

import pytest
from app.main import create_app
from app.settings import Settings
from fastapi import FastAPI
from tests.helpers import send_request

pytestmark = pytest.mark.integration


@pytest.fixture
def live_api() -> Iterator[FastAPI]:
    if os.environ.get("RUN_OLLAMA_INTEGRATION") != "1":
        pytest.skip("Set RUN_OLLAMA_INTEGRATION=1 to use a running Ollama service.")

    settings = Settings()
    yield create_app(settings=settings)


def test_real_ollama_model_list_includes_reference_model(live_api: FastAPI) -> None:
    response = send_request(live_api, "GET", "/api/v1/models")

    assert response.status_code == 200
    names = {model["name"] for model in response.json()["models"]}
    assert "qwen2.5:1.5b" in names


def test_real_ollama_generates_chat_response(live_api: FastAPI) -> None:
    response = send_request(
        live_api,
        "POST",
        "/api/v1/chat",
        json_body={
            "messages": [{"role": "user", "content": "Reply with one short greeting."}],
            "options": {"temperature": 0},
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "qwen2.5:1.5b"
    assert response.json()["message"]["content"].strip()
