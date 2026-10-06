from collections.abc import Mapping

from app.settings import Settings


def build_integration_settings(environment: Mapping[str, str]) -> Settings:
    return Settings(
        ollama_base_url=environment.get(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434",
        ),
        default_model=environment.get(
            "OLLAMA_INTEGRATION_MODEL",
            environment.get("DEFAULT_MODEL", "qwen2.5:1.5b"),
        ),
        request_timeout_seconds=environment.get(
            "OLLAMA_INTEGRATION_TIMEOUT_SECONDS",
            environment.get("REQUEST_TIMEOUT_SECONDS", "120"),
        ),
    )
