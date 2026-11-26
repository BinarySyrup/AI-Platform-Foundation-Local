from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(APIModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be blank.")
        return value


class ChatOptions(APIModel):
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)


class ChatRequest(APIModel):
    model: str | None = Field(default=None, min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    options: ChatOptions = Field(default_factory=ChatOptions)

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model name must not be blank.")
        return normalized


class HealthResponse(APIModel):
    status: Literal["ok"]


class ModelSummary(APIModel):
    name: str


class ModelListResponse(APIModel):
    models: list[ModelSummary]


class ChatResponse(APIModel):
    model: str
    message: ChatMessage


class RAGSource(APIModel):
    document_id: str
    filename: str
    page_number: int | None
    score: float | None = None


class RAGDocument(APIModel):
    document_id: str
    filename: str
    sha256: str
    size_bytes: int
    chunk_count: int


class RAGDocumentListResponse(APIModel):
    documents: list[RAGDocument]


class RAGUploadResponse(RAGDocument):
    status: Literal["indexed", "already_indexed"]


class RAGSearchRequest(APIModel):
    query: str = Field(min_length=1, max_length=32_000)
    limit: int | None = Field(default=None, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must not be blank.")
        return value


class RAGSearchResult(APIModel):
    source: RAGSource
    text: str


class RAGSearchResponse(APIModel):
    results: list[RAGSearchResult]


class RAGChatRequest(APIModel):
    model: str | None = Field(default=None, min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    options: ChatOptions = Field(default_factory=ChatOptions)

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model name must not be blank.")
        return normalized


class RAGChatResponse(APIModel):
    model: str
    message: ChatMessage
    sources: list[RAGSource]


class RAGHealthResponse(APIModel):
    status: Literal["starting", "ready", "unavailable"]
    dependencies: dict[str, Literal["ready", "unavailable"]]


class ValidationIssue(APIModel):
    field: str
    message: str
    kind: str


class ErrorDetail(APIModel):
    code: str
    message: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(APIModel):
    error: ErrorDetail
    request_id: str
