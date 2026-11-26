from pathlib import Path
from typing import Any

import httpx

from app.rag.errors import (
    RagDependencyError,
    RagError,
    RagParserError,
    RagUnprocessablePdf,
)


class DoclingClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def health(self) -> bool:
        try:
            response = await self._http_client.get("/health")
        except httpx.RequestError as exc:
            raise RagDependencyError from exc
        return response.is_success

    async def convert_pdf(self, path: Path, filename: str) -> dict[str, Any]:
        try:
            with path.open("rb") as source:
                response = await self._http_client.post(
                    "/v1/convert/file",
                    files={"files": (filename, source, "application/pdf")},
                    data={"to_formats": "json", "do_ocr": "false"},
                )
        except httpx.TimeoutException as exc:
            raise RagError(
                504,
                "ingestion_timeout",
                "PDF ingestion exceeded its configured deadline.",
            ) from exc
        except httpx.RequestError as exc:
            raise RagDependencyError from exc

        if response.status_code in (400, 422):
            raise RagUnprocessablePdf
        if response.status_code == 507:
            raise RagError(
                507, "insufficient_storage", "The PDF parser has insufficient storage."
            )
        if response.status_code >= 500:
            raise RagDependencyError
        if response.is_error:
            raise RagParserError

        try:
            payload = response.json()
        except ValueError as exc:
            raise RagParserError from exc
        if not isinstance(payload, dict):
            raise RagParserError
        return payload
