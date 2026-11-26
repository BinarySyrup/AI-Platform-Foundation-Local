from typing import Any

import httpx

from app.rag.errors import RagDependencyError, RagError, RagParserError


class QdrantClient:
    def __init__(self, http_client: httpx.AsyncClient, collection: str) -> None:
        self._http_client = http_client
        self.collection = collection
        self._collection_path = f"/collections/{collection}"

    async def health(self) -> bool:
        try:
            response = await self._http_client.get("/healthz")
        except httpx.RequestError as exc:
            raise RagDependencyError from exc
        return response.is_success

    async def initialize(self) -> None:
        try:
            response = await self._http_client.get(self._collection_path)
        except httpx.RequestError as exc:
            raise RagDependencyError from exc
        if response.status_code == 404:
            await self._create_collection()
            return
        if response.status_code == 507:
            raise RagError(
                507,
                "insufficient_storage",
                "The vector store has insufficient storage.",
            )
        if response.status_code >= 500 or response.is_error:
            raise RagDependencyError
        self._validate_collection(self._json_result(response))

    async def _create_collection(self) -> None:
        try:
            response = await self._http_client.put(
                self._collection_path,
                json={"vectors": {"size": 768, "distance": "Cosine"}},
            )
        except httpx.RequestError as exc:
            raise RagDependencyError from exc
        if response.status_code == 409:
            await self.initialize()
            return
        if response.status_code == 507:
            raise RagError(
                507,
                "insufficient_storage",
                "The vector store has insufficient storage.",
            )
        if response.status_code >= 500 or response.is_error:
            raise RagDependencyError

    @staticmethod
    def _validate_collection(payload: dict[str, Any]) -> None:
        try:
            vectors = payload["result"]["config"]["params"]["vectors"]
        except (KeyError, TypeError) as exc:
            raise RagParserError from exc
        if not isinstance(vectors, dict):
            raise RagParserError
        if vectors.get("size") != 768 or vectors.get("distance") != "Cosine":
            raise RagParserError

    @staticmethod
    def _json_result(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RagParserError from exc
        if not isinstance(payload, dict) or payload.get("status") == "error":
            raise RagParserError
        return payload

    async def delete_document(self, document_id: str) -> None:
        await self._request(
            "POST",
            f"{self._collection_path}/points/delete?wait=true",
            json_body={"filter": self._filter(document_id=document_id)},
        )

    async def delete_pending_documents(self) -> None:
        pending_ids: set[str] = set()
        offset: Any = None
        while True:
            body: dict[str, Any] = {
                "limit": 1000,
                "with_payload": ["document_id"],
                "with_vector": False,
                "filter": {"must": [{"key": "status", "match": {"value": "pending"}}]},
            }
            if offset is not None:
                body["offset"] = offset
            payload = await self._request(
                "POST",
                f"{self._collection_path}/points/scroll",
                json_body=body,
            )
            try:
                result = payload["result"]
                batch = result["points"]
                next_offset = result.get("next_page_offset")
            except (KeyError, TypeError) as exc:
                raise RagParserError from exc
            if not isinstance(batch, list):
                raise RagParserError
            for point in batch:
                if not isinstance(point, dict):
                    continue
                point_payload = point.get("payload") or {}
                document_id = (
                    point_payload.get("document_id")
                    if isinstance(point_payload, dict)
                    else None
                )
                if isinstance(document_id, str):
                    pending_ids.add(document_id)
            if next_offset is None or not batch:
                break
            offset = next_offset
        for document_id in pending_ids:
            await self.delete_document(document_id)

    async def count_ready_chunks(self) -> int:
        payload = await self._request(
            "POST",
            f"{self._collection_path}/points/count",
            json_body={
                "exact": True,
                "filter": self._filter(status="ready"),
            },
        )
        try:
            count = payload["result"]["count"]
        except (KeyError, TypeError) as exc:
            raise RagParserError from exc
        if not isinstance(count, int) or count < 0:
            raise RagParserError
        return count

    async def find_document_by_sha256(
        self,
        sha256: str,
    ) -> dict[str, Any] | None:
        records = await self.scroll(
            query_filter={
                "must": [
                    {"key": "sha256", "match": {"value": sha256}},
                    {"key": "status", "match": {"value": "ready"}},
                ]
            },
            with_payload=[
                "document_id",
                "filename",
                "sha256",
                "size_bytes",
                "chunk_count",
            ],
            limit=1,
        )
        if not records:
            return None
        return records[0][1]

    async def upsert(self, points: list[dict[str, Any]]) -> None:
        await self._request(
            "PUT",
            f"{self._collection_path}/points?wait=true",
            json_body={"points": points},
        )

    async def mark_document_ready(self, document_id: str) -> None:
        await self._request(
            "POST",
            f"{self._collection_path}/points/payload?wait=true",
            json_body={
                "payload": {"status": "ready"},
                "filter": self._filter(document_id=document_id, status="pending"),
            },
        )

    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        payload = await self._request(
            "POST",
            f"{self._collection_path}/points/search",
            json_body={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
                "filter": self._filter(status="ready"),
            },
        )
        result = payload.get("result")
        if not isinstance(result, list):
            raise RagParserError
        return [point for point in result if isinstance(point, dict)]

    async def scroll(
        self,
        *,
        query_filter: dict[str, Any] | None = None,
        with_payload: bool | list[str] = True,
        limit: int = 1000,
    ) -> list[tuple[Any, dict[str, Any]]]:
        points: list[tuple[Any, dict[str, Any]]] = []
        offset: Any = None
        while True:
            body: dict[str, Any] = {
                "limit": limit,
                "with_payload": with_payload,
                "with_vector": False,
            }
            if query_filter is not None:
                body["filter"] = query_filter
            if offset is not None:
                body["offset"] = offset
            payload = await self._request(
                "POST",
                f"{self._collection_path}/points/scroll",
                json_body=body,
            )
            try:
                result = payload["result"]
                batch = result["points"]
                next_offset = result.get("next_page_offset")
            except (KeyError, TypeError) as exc:
                raise RagParserError from exc
            if not isinstance(batch, list):
                raise RagParserError
            for point in batch:
                if isinstance(point, dict):
                    point_payload = point.get("payload") or {}
                    if isinstance(point_payload, dict):
                        points.append((point.get("id"), point_payload))
            if next_offset is None or not batch:
                return points
            offset = next_offset

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = await self._http_client.request(method, path, json=json_body)
        except httpx.RequestError as exc:
            raise RagDependencyError from exc
        if response.status_code == 507:
            raise RagError(
                507,
                "insufficient_storage",
                "The vector store has insufficient storage.",
            )
        if response.status_code >= 500 or response.is_error:
            raise RagDependencyError
        return self._json_result(response)

    @staticmethod
    def _filter(**conditions: str) -> dict[str, Any]:
        return {
            "must": [
                {"key": key, "match": {"value": value}}
                for key, value in conditions.items()
            ]
        }
