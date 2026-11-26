import re
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=None,
        extra="ignore",
    )

    ollama_base_url: AnyHttpUrl = "http://ollama:11434"
    default_model: str = "llama3.1:8b"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    request_timeout_seconds: float = Field(
        default=120,
        gt=0,
        le=3600,
        allow_inf_nan=False,
    )
    docling_base_url: AnyHttpUrl = "http://docling:5001"
    qdrant_base_url: AnyHttpUrl = "http://qdrant:6333"
    rag_collection_name: str = "platform_documents"
    rag_ingestion_timeout_seconds: float = Field(
        default=120,
        gt=0,
        le=3600,
        allow_inf_nan=False,
    )
    rag_max_indexed_chunks: int | None = Field(default=25_000, ge=1)
    rag_max_pdf_pages: int | None = Field(default=None, ge=1)
    rag_score_threshold: float | None = Field(
        default=0.5,
        ge=0,
        le=1,
        allow_inf_nan=False,
    )

    @field_validator("rag_collection_name")
    @classmethod
    def validate_collection_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("rag_collection_name contains unsupported characters.")
        return value
