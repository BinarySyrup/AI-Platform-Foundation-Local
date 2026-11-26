from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import get_rag, get_runtime, get_settings
from app.clients.protocol import RuntimeClient
from app.models.schemas import (
    ChatMessage,
    RAGChatRequest,
    RAGChatResponse,
    RAGDocumentListResponse,
    RAGHealthResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResult,
    RAGUploadResponse,
)
from app.rag.service import NO_SUPPORT_ANSWER, RagService
from app.settings import Settings

rag_router = APIRouter(tags=["RAG"])


@rag_router.get(
    "/health/rag",
    response_model=RAGHealthResponse,
    responses={503: {"model": RAGHealthResponse}},
    summary="Check RAG readiness",
)
async def rag_health(
    response: Response,
    rag: Annotated[RagService, Depends(get_rag)],
) -> RAGHealthResponse:
    health = rag.health()
    if health["status"] != "ready":
        response.status_code = 503
    return RAGHealthResponse(**health)


@rag_router.post(
    "/api/v1/knowledge/documents",
    response_model=RAGUploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        201: {"model": RAGUploadResponse},
        400: {"description": "Invalid multipart upload."},
        413: {"description": "PDF exceeds the 1 GB limit."},
        415: {"description": "Only PDF documents are supported."},
        422: {"description": "PDF could not be processed."},
        429: {"description": "Another upload is in progress."},
        502: {"description": "PDF parser returned an invalid response."},
        503: {"description": "RAG is unavailable or not configured."},
        504: {"description": "Ingestion deadline exceeded."},
        507: {"description": "Temporary storage is full."},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
    summary="Upload and index a PDF",
)
async def upload_document(
    request: Request,
    response: Response,
    rag: Annotated[RagService, Depends(get_rag)],
) -> RAGUploadResponse:
    document, created = await rag.ingest_request(request)
    response.status_code = 201 if created else 200
    return RAGUploadResponse(
        **document.model_dump(),
        status="indexed" if created else "already_indexed",
    )


@rag_router.get(
    "/api/v1/knowledge/documents",
    response_model=RAGDocumentListResponse,
    summary="List indexed documents",
)
async def list_documents(
    rag: Annotated[RagService, Depends(get_rag)],
) -> RAGDocumentListResponse:
    return RAGDocumentListResponse(documents=await rag.list_documents())


@rag_router.delete(
    "/api/v1/knowledge/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Document not found."}},
    summary="Delete an indexed document",
)
async def delete_document(
    document_id: str,
    rag: Annotated[RagService, Depends(get_rag)],
) -> Response:
    await rag.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@rag_router.post(
    "/api/v1/knowledge/search",
    response_model=RAGSearchResponse,
    summary="Search indexed passages",
)
async def search_documents(
    body: RAGSearchRequest,
    rag: Annotated[RagService, Depends(get_rag)],
) -> RAGSearchResponse:
    hits = await rag.search(body.query, limit=body.limit)
    return RAGSearchResponse(
        results=[RAGSearchResult(source=hit.source, text=hit.text) for hit in hits]
    )


@rag_router.post(
    "/api/v1/rag/chat",
    response_model=RAGChatResponse,
    responses={
        404: {"description": "Generation model not found."},
        503: {"description": "RAG is unavailable or not calibrated."},
        504: {"description": "Model runtime timed out."},
    },
    summary="Answer using indexed documents",
)
async def rag_chat(
    body: RAGChatRequest,
    runtime: Annotated[RuntimeClient, Depends(get_runtime)],
    rag: Annotated[RagService, Depends(get_rag)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RAGChatResponse:
    model = body.model or settings.default_model
    prompt = await rag.prepare_prompt(body.messages)
    if prompt.no_support:
        answer = NO_SUPPORT_ANSWER
    else:
        response = await runtime.chat(
            model=model,
            messages=prompt.messages,
            temperature=body.options.temperature,
        )
        answer = response.message.content
    return RAGChatResponse(
        model=model,
        message=ChatMessage(
            role="assistant",
            content=rag.add_citations(answer, prompt.sources),
        ),
        sources=prompt.sources,
    )
