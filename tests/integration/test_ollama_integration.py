import os
from collections.abc import Iterator

import pytest
from app.main import create_app
from app.settings import Settings
from fastapi import FastAPI
from tests.helpers import send_request
from tests.integration_config import build_integration_settings

pytestmark = pytest.mark.integration


@pytest.fixture
def integration_settings() -> Settings:
    if os.environ.get("RUN_OLLAMA_INTEGRATION") != "1":
        pytest.skip("Set RUN_OLLAMA_INTEGRATION=1 to use a running Ollama service.")

    return build_integration_settings(os.environ)


@pytest.fixture
def live_api(integration_settings: Settings) -> Iterator[FastAPI]:
    yield create_app(settings=integration_settings)


def test_real_ollama_model_list_includes_configured_model(
    live_api: FastAPI,
    integration_settings: Settings,
) -> None:
    response = send_request(live_api, "GET", "/api/v1/models")

    assert response.status_code == 200
    names = {model["name"] for model in response.json()["models"]}
    assert integration_settings.default_model in names


def test_real_ollama_generates_chat_response(
    live_api: FastAPI,
    integration_settings: Settings,
) -> None:
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
    assert response.json()["model"] == integration_settings.default_model
    assert response.json()["message"]["content"].strip()
