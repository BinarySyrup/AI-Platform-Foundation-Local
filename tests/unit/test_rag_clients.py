import asyncio
import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from app.clients.docling import DoclingClient
from app.clients.qdrant import QdrantClient
from app.rag.errors import RagDependencyError, RagParserError, RagUnprocessablePdf


def make_client(
    base_url: str,
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )


def test_docling_uploads_pdf_with_configured_conversion_options(tmp_path: Path) -> None:
    pdf_path = tmp_path / "synthetic.pdf"
    pdf_path.write_bytes(b"%PDF-synthetic")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"document": {"json_content": {"texts": []}}},
        )

    async def operation() -> dict[str, object]:
        async with make_client("http://docling:5001", handler) as http_client:
            return await DoclingClient(http_client).convert_pdf(pdf_path, "guide.pdf")

    payload = asyncio.run(operation())
    request = requests[0]
    request_body = request.read()

    assert request.method == "POST"
    assert request.url.path == "/v1/convert/file"
    assert b'name="files"; filename="guide.pdf"' in request_body
    assert b'name="to_formats"' in request_body
    assert b"json" in request_body
    assert b'name="do_ocr"' in request_body
    assert b"false" in request_body
    assert b"%PDF-synthetic" in request_body
    assert payload["document"]["json_content"]["texts"] == []


def test_docling_maps_unprocessable_pdf_response(tmp_path: Path) -> None:
    pdf_path = tmp_path / "bad.pdf"
    pdf_path.write_bytes(b"%PDF-synthetic")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "not a PDF"})

    async def operation() -> None:
        async with make_client("http://docling:5001", handler) as http_client:
            await DoclingClient(http_client).convert_pdf(pdf_path, "bad.pdf")

    with pytest.raises(RagUnprocessablePdf):
        asyncio.run(operation())


def test_qdrant_initialization_creates_expected_vector_schema() -> None:
    calls: list[tuple[str, str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.read()))
        if request.method == "GET":
            return httpx.Response(404, json={"status": "error"})
        return httpx.Response(200, json={"result": True, "status": "ok"})

    async def operation() -> None:
        async with make_client("http://qdrant:6333", handler) as http_client:
            await QdrantClient(http_client, "platform_documents").initialize()

    asyncio.run(operation())

    assert calls[0][:2] == ("GET", "/collections/platform_documents")
    assert calls[1][:2] == ("PUT", "/collections/platform_documents")
    assert json.loads(calls[1][2]) == {"vectors": {"size": 768, "distance": "Cosine"}}


def test_qdrant_rejects_incompatible_existing_vector_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": {
                    "config": {
                        "params": {"vectors": {"size": 384, "distance": "Cosine"}}
                    }
                },
                "status": "ok",
            },
        )

    async def operation() -> None:
        async with make_client("http://qdrant:6333", handler) as http_client:
            await QdrantClient(http_client, "platform_documents").initialize()

    with pytest.raises(RagParserError):
        asyncio.run(operation())


def test_qdrant_search_uses_ready_filter_and_returns_scores() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"result": [{"id": "point-a", "score": 0.8}]})

    async def operation() -> list[dict[str, object]]:
        async with make_client("http://qdrant:6333", handler) as http_client:
            return await QdrantClient(http_client, "platform_documents").search(
                [0.25] * 768,
                limit=5,
            )

    points = asyncio.run(operation())
    body = json.loads(requests[0].read())

    assert requests[0].method == "POST"
    assert requests[0].url.path == "/collections/platform_documents/points/search"
    assert body["limit"] == 5
    assert body["with_payload"] is True
    assert body["filter"] == {"must": [{"key": "status", "match": {"value": "ready"}}]}
    assert points == [{"id": "point-a", "score": 0.8}]


def test_qdrant_maps_connection_failures_without_upstream_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private host detail", request=request)

    async def operation() -> None:
        async with make_client("http://qdrant:6333", handler) as http_client:
            await QdrantClient(http_client, "platform_documents").count_ready_chunks()

    with pytest.raises(RagDependencyError) as raised:
        asyncio.run(operation())

    assert "private host detail" not in str(raised.value)
