# Platform API

This directory contains the FastAPI application, its Ollama adapter, and the
API container image. Terraform builds the API image and connects it to Open
WebUI, Ollama, Docling Serve, and Qdrant. FastAPI is the only client-facing
service and owns the RAG workflow.

The RAG additions described here are the target API contract; implementation
is pending.

## Docker Deployment

The API runs in the Terraform-managed Docker environment. It reaches Ollama at
`http://ollama:11434` on the private runtime network, Open WebUI at
`http://api:8000/v1` on the client network, and Docling Serve and Qdrant on the
private RAG network. Only the API and Open WebUI publish loopback host ports.
Ollama, Docling Serve, and Qdrant have no host port mappings.

Ollama-specific HTTP details remain inside the runtime adapter. PDF conversion
and Qdrant operations use separate adapters so their service contracts do not
leak into routes or schemas.

## Existing API

- `GET /` returns an HTML landing page with the current API version.
- `GET /health` reports API liveness without contacting Ollama.
- `GET /api/v1/models` returns available Ollama chat model names.
- `POST /api/v1/chat` accepts 1–100 non-blank messages with `system`, `user`,
  or `assistant` roles. `model` is optional and defaults to `DEFAULT_MODEL`;
  `options.temperature` is optional and must be between 0 and 2.
- `GET /v1/models` lists models using the OpenAI-compatible format.
- `POST /v1/chat/completions` supports JSON and server-sent event streaming.
- Swagger UI is available at `/docs`; the OpenAPI schema is at `/openapi.json`
  and ReDoc is at `/redoc`.

## RAG Model Choices

The OpenAI-compatible model list will include a direct entry and a RAG alias
for each supported Ollama chat model. For example, `llama3.1:8b` sends the
conversation directly to Ollama; `llama3.1:8b-rag` retrieves passages and
then calls the same `llama3.1:8b` generation model. FastAPI resolves the alias
explicitly. The alias is not passed to Ollama, and it does not represent an
additional model download.

RAG requests embed the latest user message using the fixed
`nomic-embed-text:v1.5` model, search Qdrant, and add relevant source-labelled
chunks to the selected model's context. The embedding model is not listed as a
chat model. If no passages meet the configured relevance threshold, the RAG
path reports that the documents do not provide enough information. If the
parser, embedding, or vector store is unavailable, the request fails rather
than silently bypassing retrieval.

## Document API Target

The planned document routes are:

- `POST /api/v1/knowledge/documents` — upload a bounded PDF for indexing.
- `GET /api/v1/knowledge/documents` — list indexed document metadata.
- `DELETE /api/v1/knowledge/documents/{document_id}` — delete the document's
  chunks from Qdrant.
- `POST /api/v1/knowledge/search` — inspect retrieved chunks and sources.
- `POST /api/v1/rag/chat` — use the native platform contract and return
  structured source references.

FastAPI sends PDF bytes to Docling Serve's file-conversion endpoint. It does
not use URL-based conversion. The API preserves page/source metadata, chunks
the extracted text, calls Ollama for embeddings, and stores chunk text,
vectors, and metadata in Qdrant. The initial input format is PDF. OCR for
scanned PDFs remains deferred until resource use and page citations pass
validation.

RAG responses cite the PDF name and page where available. Retrieved text is
treated as untrusted context and is never written to application logs by
default. Source documents are not retained by the parser service after
conversion; indexed chunk text and metadata remain in Qdrant until deleted.
The platform's raw-PDF retention policy must be confirmed before
implementation.

## Errors and Logging

Errors use a stable response shape and request ID. Logs include method, path,
status, duration, and request ID, but not prompts, document content, retrieved
chunks, or generated responses. RAG dependency failures are explicit and
include safe errors for Docling, Ollama embeddings, and Qdrant connectivity.

The platform API does not authenticate requests in this local release. Keep
FastAPI and Open WebUI published on loopback, and keep the RAG services on
private Docker networks with no host ports.

## Tests and Container Image

Run unit tests and lint checks from the repository root:

```powershell
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

RAG tests will cover parser response mapping, page metadata, chunking,
embedding translation, vector upsert/search/delete, model alias routing,
citations, no-match behavior, and dependency errors. Deployment checks will
use a synthetic PDF and avoid assertions on exact generated wording.

Terraform builds the API image from `platform/Dockerfile`. The image listens on
port 8000 inside the container. Publish it on `127.0.0.1` only.
