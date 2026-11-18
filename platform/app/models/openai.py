from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import ChatMessage


class OpenAIModel(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "local-ai-platform"


class OpenAIModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[OpenAIModel]


class OpenAIChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = Field(min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    stream: bool = False


class OpenAIChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: Literal["stop"] = "stop"


class OpenAIChatResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChatChoice]
