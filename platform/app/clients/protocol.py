from collections.abc import AsyncIterator
from typing import Protocol

from app.models.schemas import ChatMessage, ChatResponse, ModelSummary


class RuntimeClient(Protocol):
    async def list_models(self) -> list[ModelSummary]: ...

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
    ) -> ChatResponse: ...

    def chat_stream(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
    ) -> AsyncIterator[str]: ...


class EmbeddingClient(Protocol):
    async def embed(
        self,
        *,
        model: str,
        inputs: list[str],
    ) -> list[list[float]]: ...
