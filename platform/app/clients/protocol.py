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
