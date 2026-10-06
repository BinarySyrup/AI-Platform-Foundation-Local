from tests.integration_config import build_integration_settings


def test_integration_settings_use_local_defaults() -> None:
    settings = build_integration_settings({})

    assert str(settings.ollama_base_url).rstrip("/") == "http://127.0.0.1:11434"
    assert settings.default_model == "qwen2.5:1.5b"
    assert settings.request_timeout_seconds == 120


def test_integration_settings_support_environment_overrides() -> None:
    settings = build_integration_settings(
        {
            "OLLAMA_BASE_URL": "http://ollama-host:11434",
            "DEFAULT_MODEL": "qwen2.5:3b",
            "OLLAMA_INTEGRATION_MODEL": "llama3.2:3b",
            "REQUEST_TIMEOUT_SECONDS": "60",
            "OLLAMA_INTEGRATION_TIMEOUT_SECONDS": "240",
        }
    )

    assert str(settings.ollama_base_url).rstrip("/") == "http://ollama-host:11434"
    assert settings.default_model == "llama3.2:3b"
    assert settings.request_timeout_seconds == 240


def test_default_model_is_used_when_integration_model_is_not_set() -> None:
    settings = build_integration_settings({"DEFAULT_MODEL": "phi4:mini"})

    assert settings.default_model == "phi4:mini"
