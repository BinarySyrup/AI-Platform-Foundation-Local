# Platform API

This directory contains the FastAPI application and its Ollama, Docling Serve,
and Qdrant adapters. Terraform builds the API image and connects it to Open
WebUI, Ollama, Docling Serve, and Qdrant. FastAPI owns model routing and the
local PDF retrieval workflow.

## API Routes

- `GET /health` reports process liveness without checking dependencies.
- `GET /health/rag` reports `starting`, `ready`, or `unavailable` and the
  Ollama embedding, Docling, and Qdrant dependency states. Startup retries
  recovery/readiness until dependencies are available; RAG routes return HTTP
  503 until then.
- `GET /api/v1/models` lists installed chat models and omits
  `nomic-embed-text:v1.5`.
- `POST /api/v1/chat` sends non-streaming direct chat to the selected Ollama
  model.
- `GET /v1/models` always lists direct chat entries and adds `<model>-rag`
  aliases after RAG is ready. The aliases
  resolve to the same installed generation model. Alias creation skips names
  that collide with real models.
- `POST /v1/chat/completions` supports direct and RAG requests in JSON or
  server-sent event format. RAG answers include source and page citations.
- `POST /api/v1/knowledge/documents` streams one PDF from a
  `multipart/form-data` request with a `file` field, converts it through
  Docling, chunks it, embeds it, and stores it in Qdrant.
- `GET /api/v1/knowledge/documents` lists ready documents.
- `DELETE /api/v1/knowledge/documents/{document_id}` removes all indexed chunks
  for a document.
- `POST /api/v1/knowledge/search` returns matching passages and source metadata.
- `POST /api/v1/rag/chat` returns a grounded answer and structured source
  metadata.

Swagger UI is at `/docs`, OpenAPI is at `/openapi.json`, and ReDoc is at
`/redoc`. Document management is available through Swagger UI or `curl.exe`.
Open WebUI provides chat and model selection.

## RAG Processing

FastAPI calls Docling Serve's `/v1/convert/file` endpoint with the PDF bytes;
it does not use URL conversion. The API reads structured Docling JSON, keeps
chunks within one source page and heading section, and stores filename, SHA-256
document ID, page, and chunk metadata in Qdrant. The chunker targets 600
deterministic lexical token units with 100 units of overlap. This is a
lightweight approximation of model tokens; quality evaluation may justify a
tokenizer-specific implementation or different chunk settings.

Ollama embeds chunks with `search_document:` and queries with `search_query:`
using the fixed `nomic-embed-text:v1.5` model. The API validates the 768-value
embedding size and creates or validates a Qdrant collection using Cosine
distance. RAG chat uses the selected direct model's underlying Ollama model,
and treats retrieved text as untrusted context. It returns the no-support
answer when no result meets the configured threshold; it never silently falls
back to direct chat. The generation prompt includes at most 24,000 characters
of retrieved excerpts.

The score threshold defaults to a provisional `0.50` for initial use. Compare
paired prefixes with raw inputs on the separate calibration set, then adjust
`rag_score_threshold` in the API's runtime configuration if needed. RAG chat
uses the provisional cutoff before calibration; the held-out 30-question
quality acceptance set is still required before treating retrieval quality as
validated.

Uploads are limited to PDF files with a 1 GB (1,000,000,000 byte) maximum and
one active upload. The configurable `RAG_INGESTION_TIMEOUT_SECONDS` deadline
defaults to 120 seconds and covers request streaming through completed
indexing. The API streams multipart data directly to a per-upload temporary
file, calculates SHA-256 during transfer, and removes temporary files and
partial Qdrant points on terminal paths. Identical bytes reuse the first
successful document record and index. Startup removes abandoned scratch
directories and deletes all points belonging to documents with `pending`
points before RAG readiness is enabled.

`RAG_MAX_INDEXED_CHUNKS` defaults to a provisional 25,000. Measure Qdrant
storage growth on the target host and adjust that limit before treating it as
validated. `RAG_MAX_PDF_PAGES` is optional and remains unset pending
target-host timing and resource measurements. The 1 GB file ceiling does not
guarantee completion within the deadline.

## Configuration and Deployment

The API reads process environment variables. Terraform supplies the container
environment; `.env.example` documents local settings and is not loaded
automatically. Ollama, Docling, and Qdrant use private container networks. Only
FastAPI and Open WebUI publish loopback host ports; the internal services have
no host mappings.

RAG environment settings include:

- `DOCLING_BASE_URL` and `QDRANT_BASE_URL` for internal service addresses.
- `RAG_COLLECTION_NAME` for the Qdrant collection.
- `RAG_INGESTION_TIMEOUT_SECONDS` for the full upload/index deadline.
- `RAG_MAX_INDEXED_CHUNKS` for the provisional 25,000-chunk logical cap.
- `RAG_MAX_PDF_PAGES` for an optional practical page limit.
- `RAG_SCORE_THRESHOLD` for the provisional 0.50 relevance cutoff; tune after calibration.

See the [Terraform guide](../infra/terraform/README.md) for pinned image
digests, configuration, health checks, setup, and data retention.

## Remaining Development Checks

RAG-specific unit tests now cover the core service and client behavior. The
held-out quality evaluation runner is available at
`scripts/rag_quality_eval.py`; run it against the deployed stack after
calibration. The target-host benchmark must establish the practical page
limit, validate or revise the provisional `RAG_MAX_INDEXED_CHUNKS` value, and
establish the ongoing manual disk reserve. Review the
[project scope](../docs/project-scope.md) and
[Architecture Decision 0001](../docs/decisions/0001-local-rag-architecture.md)
for the complete implementation and release gates.
