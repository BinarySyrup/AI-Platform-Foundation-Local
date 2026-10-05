from typing import Any

import httpx

from app.models.schemas import ChatMessage, ChatResponse, ModelSummary


class OllamaError(Exception):
    pass


class RuntimeUnavailable(OllamaError):
    pass


class RuntimeTimeout(OllamaError):
    pass


class ModelNotFound(OllamaError):
    pass


class RuntimeResponseError(OllamaError):
    pass


class RuntimeProtocolError(OllamaError):
    pass


class OllamaClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def list_models(self) -> list[ModelSummary]:
        payload = await self._request("GET", "/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise RuntimeProtocolError("Ollama returned an invalid model list.")

        summaries: list[ModelSummary] = []
        for model in models:
            if not isinstance(model, dict):
                raise RuntimeProtocolError("Ollama returned an invalid model entry.")
            name = model.get("name") or model.get("model")
            if not isinstance(name, str) or not name:
                raise RuntimeProtocolError("Ollama returned a model without a name.")
            summaries.append(ModelSummary(name=name))
        return summaries

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
    ) -> ChatResponse:
        body: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
        }
        if temperature is not None:
            body["options"] = {"temperature": temperature}

        payload = await self._request(
            "POST",
            "/api/chat",
            json_body=body,
            map_missing_model=True,
        )
        message = payload.get("message")
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("content"), str)
            or not message["content"].strip()
        ):
            raise RuntimeProtocolError("Ollama returned an invalid chat response.")

        response_model = payload.get("model")
        selected_model = (
            response_model
            if isinstance(response_model, str) and response_model
            else model
        )
        return ChatResponse(
            model=selected_model,
            message=ChatMessage(role="assistant", content=message["content"]),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        map_missing_model: bool = False,
    ) -> dict[str, Any]:
        try:
            response = await self._http_client.request(method, path, json=json_body)
        except httpx.TimeoutException as exc:
            raise RuntimeTimeout from exc
        except httpx.RequestError as exc:
            raise RuntimeUnavailable from exc

        if response.status_code == 404 and map_missing_model:
            raise ModelNotFound
        if response.status_code >= 500:
            raise RuntimeUnavailable
        if response.is_error:
            raise RuntimeResponseError

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeProtocolError from exc
        if not isinstance(payload, dict):
            raise RuntimeProtocolError("Ollama returned an invalid response.")
        return payload
