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

## Planned RAG Readiness API

`GET /health/rag` will report RAG readiness and dependency state. It returns
HTTP 200 only when startup recovery is complete and Qdrant, Docling Serve, and
the Ollama embedding model are available; it returns HTTP 503 while RAG is
starting or unavailable. RAG routes return HTTP 503 until ready. This endpoint
is independent of `/health`: RAG dependency failures do not make the API
process fail its liveness check. Direct chat can remain available through
Ollama while RAG is starting or unavailable; liveness and direct-chat routes
remain served while startup recovery runs.

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

Use the model's default 768-dimensional vectors with Qdrant Cosine distance.
The API validates embedding output size and collection schema before marking
RAG ready; a mismatch keeps RAG unavailable. Changing the model, vector
dimension, distance metric, or input prefix convention requires rebuilding
the collection from source PDFs.

The initial retrieval profile preserves Docling paragraph and heading
boundaries and PDF page metadata, targeting 600 tokens per chunk with 100
tokens of overlap. It uses vector-only search and returns the top 5 chunks.
Hybrid search and reranking are deferred. Use `search_document:` for chunks and
`search_query:` for queries. Compare these paired prefixes with raw inputs on a
separate small calibration set, then set the relevance threshold from
answerable and unanswerable score results. Do not tune against the held-out
quality set. Changing chunk size, overlap, or prefix convention requires
rebuilding the Qdrant index.

The post-development quality acceptance set contains 30 questions across
6 to 10 synthetic PDFs: 20 answerable and 10 unanswerable. It passes with at
least 18 correct, evidence-grounded answers out of 20, correct source and page
for every citation, and a no-support response for all 10 unanswerable questions.

## Document API Target

The planned document routes are:

- `POST /api/v1/knowledge/documents` — synchronously upload and index a PDF up
  to 1 GB (1,000,000,000 bytes) using the `file` field in
  `multipart/form-data`.
- `GET /api/v1/knowledge/documents` — list indexed document metadata.
- `DELETE /api/v1/knowledge/documents/{document_id}` — delete the document's
  chunks from Qdrant.
- `POST /api/v1/knowledge/search` — inspect retrieved chunks and sources.
- `POST /api/v1/rag/chat` — use the native platform contract and return
  structured source references.

Users can upload, list, and delete documents through Swagger UI at `/docs` or
with `curl.exe`. Open WebUI provides chat and model selection; document
management uses these FastAPI endpoints. See the [Getting Started guide](../docs/getting-started.md)
for upload, list, and delete examples.

FastAPI sends PDF bytes to Docling Serve's file-conversion endpoint. It does
not use URL-based conversion. The API preserves page/source metadata, chunks
the extracted text, calls Ollama for embeddings, and stores chunk text,
vectors, and metadata in Qdrant. The initial input format is PDF. OCR for
scanned PDFs remains deferred until resource use and page citations pass
validation.

The synchronous deadline is controlled by `RAG_INGESTION_TIMEOUT_SECONDS` and
defaults to 120 seconds for the entire request, including file transfer through
completed indexing. One upload may run at a time; another request receives
HTTP 429 immediately and is not queued. FastAPI streams the request to bounded
temporary storage rather than buffering the entire PDF in memory. Temporary
files and partial Qdrant points are removed on success, failure, timeout, and
cancellation. The 1 GB cap is a hard ceiling, not a promise that each file
will finish within 120 seconds; the practical page limit must be benchmarked.

The collection has a configurable `RAG_MAX_INDEXED_CHUNKS` cap. FastAPI checks
the existing ready chunk count plus the new document's chunks after chunking
and before embedding or Qdrant writes. An upload that would exceed the cap is
rejected with a capacity-limit error and its temporary files are cleaned up.
Identical-byte retries use the existing index; deleting a document releases
its chunks. The default cap is set from target-host storage measurements. It
limits logical index size and does not impose a physical disk quota.

Each upload uses a unique scratch directory in the API container's writable
filesystem, not a named volume. The API removes it during normal cleanup and
sweeps leftover upload directories at startup. Qdrant chunks start as
`pending`; retrieval and document listing expose only `ready` documents. Once
all chunks are indexed, FastAPI marks the document ready. At startup, documents
with any pending chunks are identified and all their points are deleted before
RAG operations are enabled. This also handles a crash during ready-state
publication. The initial deployment uses one API container and one worker;
multiple workers would need coordinated cleanup.

FastAPI computes SHA-256 while streaming and uses the digest as the document
ID. A new successful upload returns HTTP 201. An exact-byte duplicate returns
HTTP 200 with the existing document metadata and reuses its index. The filename
from the first successful upload remains canonical. A same-name PDF with
different bytes is indexed as a separate document; it does not overwrite the
existing one.

RAG responses cite the PDF name and page where available. Retrieved text is
treated as untrusted context and is never written to application logs by
default. The platform processes original PDFs transiently and does not retain
them after ingestion. Users keep source PDFs outside the platform for
re-indexing. Temporary upload and conversion files must be removed after
processing, including failure paths. Extracted chunk text, vectors, and source
metadata remain in Qdrant until deleted. Deleting a document removes its index
entries but does not affect the user's external PDF. The initial release does
not create Qdrant snapshots. If the index is lost, recreate it by uploading
the source PDFs again. The Qdrant volume persists across routine teardown but
does not protect against volume loss.

## Errors and Logging

Errors use a stable response shape and request ID. Logs include method, path,
status, duration, and request ID, but not prompts, document content, retrieved
chunks, or generated responses. RAG dependency failures are explicit and
include safe errors for Docling, Ollama embeddings, and Qdrant connectivity.
Concurrent ingestion is rejected with HTTP 429; an ingestion that exceeds its
configured deadline returns a timeout error and leaves no partial document in
the index.

RAG failures use stable error codes: 413 `file_too_large`, 415
`unsupported_media_type`, 422 for malformed, encrypted, page-limit, and
no-extractable-text PDFs, 409 `indexed_chunk_limit_exceeded`, 429
`upload_in_progress`, 504 `ingestion_timeout`, 503 `rag_not_ready` or
`dependency_unavailable`, 502 `parser_upstream_error`, and 507
`insufficient_storage` for actual disk exhaustion; unexpected failures use 500
`internal_error`. Native API errors include a safe message, request ID, and
`X-Request-ID` header; OpenAI-compatible routes translate the error to the
OpenAI response shape. All failures clean temporary files and partial index
points.

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

RAG tests will cover parser response mapping, page metadata, PDF upload size
validation, exact-byte duplicate detection, idempotent retries, timeout and
cancellation cleanup, concurrent-upload rejection, partial-index rollback,
startup recovery after an interrupted upload, chunking, embedding translation, vector
upsert/search/delete, model alias routing, citations, no-match behavior, and
dependency errors. Deployment checks will use a synthetic PDF and avoid
assertions on exact generated wording.

Terraform builds the API image from `platform/Dockerfile`. The image listens on
port 8000 inside the container. Publish it on `127.0.0.1` only.
