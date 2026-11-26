# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Implement PDF ingestion, local Docling conversion, Nomic embeddings, Qdrant
  indexing and search, document listing/deletion, and native RAG chat.
- Add OpenAI-compatible direct and RAG model entries, with retrieval aliases
  mapped to the selected installed Ollama generation model.
- Provision private Docker networking, Docling Serve and Qdrant containers, and
  persistent Qdrant storage through Terraform.
- Add separate RAG readiness, startup cleanup for abandoned uploads and pending
  index points, exact-byte upload deduplication, and bounded synchronous upload.

### Documentation

- Add the local PDF RAG target architecture, Docling Serve and Qdrant roles,
  embedding-model decision, API workflow, operational constraints, and ADR.
- Decide to process uploaded PDFs transiently, keep originals user-managed
  outside the platform, and persist the extracted Qdrant index. Select
  re-uploading those PDFs as the initial release's index recovery method;
  snapshots and automated Qdrant backups are out of scope.
- Define synchronous PDF ingestion with a 1 GB (1,000,000,000-byte) hard
  upload ceiling, a configurable 120-second end-to-end deadline, one active
  upload, and temporary file/partial-index cleanup.
- Set Windows with Docker Desktop/WSL2 as the primary validation environment
  and define an 8-core x86-64, 32 GiB RAM target with about 24 GiB available to
  Docker and SSD storage with 50 GB free before setup. Mark 10 GB after setup
  as a provisional planning target; use target-host benchmarks to set ongoing
  free-space needs for temporary processing and Qdrant growth.
- Define exact-byte PDF deduplication using a streaming SHA-256 digest, with
  retries reusing the existing index and new bytes treated as a separate file.
- Define crash cleanup using API-container scratch directories and startup
  removal of abandoned files and pending Qdrant points before RAG is enabled.
- Keep `/health` as API liveness and add a separate RAG readiness endpoint;
  gate RAG routes with HTTP 503 until recovery and dependencies are ready.
- Set the initial retrieval baseline to page-aware 600-token chunks with
  100-token overlap, vector-only search, and top 5 results; use Nomic's paired
  retrieval prefixes and calibrate the relevance threshold on a separate
  synthetic set.
- Define a held-out, post-development quality check with 30 questions across
  6 to 10 synthetic PDFs (20 answerable, 10 unanswerable), including answer
  grounding, citation accuracy, and no-support acceptance criteria.
- Add a configurable collection-wide indexed-chunk cap, with its numeric value
  set from target-host Qdrant storage measurements; document that it is a
  logical limit rather than a physical disk quota.
- Fix the initial vector schema at 768 dimensions with Qdrant Cosine distance;
  rebuild the index if the embedding input convention changes.
- Select `qdrant/qdrant:v1.20.2`; record its immutable digest before deployment.
- Select Docling Serve CPU `v1.38.2`; record its immutable digest before
  deployment.
- Define RAG upload and dependency error statuses and stable error codes,
  including separate responses for logical index capacity and physical disk
  exhaustion.
- Document Swagger UI and `curl.exe` workflows for uploading, listing, and
  deleting RAG documents.
- Document that RAG chat requires a calibration-derived score threshold and
  ingestion requires a benchmark-derived indexed-chunk limit. Numeric values
  remain unset until calibration and target-host measurements are complete.

## [1.2.0] - 2026-11-17

### Added

- Open WebUI image `openwebui/open-webui:0.13.4` as the local chat interface, with persistent UI data and
  separate client and runtime Docker networks.
- OpenAI-compatible model listing and streaming or non-streaming chat
  completions in the FastAPI platform API.

### Changed

- Bump the platform API and local API image to 1.2.0.
- Pin Ollama to `ollama/ollama:0.40.16`.
- Keep the API independently accessible and route Open WebUI requests through
  FastAPI, with Ollama isolated on the runtime network.

## [1.1.0] - 2026-10-28

### Added

- Architecture diagram and README guidance for verifying Terraform resources,
  container health, model availability, and API connectivity.

### Changed

- Bump the API and container image to 1.1.0, upgrade Terraform to 1.17.0, and
  update the pinned FastAPI, Pydantic, pytest, and Ruff versions.
- Remove the Terraform-managed Ollama image on destroy while preserving the
  model volume; document cleanup for images retained by earlier destroys.
- Clarify model selection and remove the repository tree from the README.
- Set the Mermaid infrastructure diagram to a top-to-bottom layout.

## [1.0.0] - 2026-10-06

### Added

- Terraform-managed Docker deployment with a private network, FastAPI API and
  Ollama containers, and a persistent model volume.
- Versioned API endpoints for the HTML landing page, health, model listing, and
  non-streaming chat, with validated schemas, normalized errors, and request IDs.
- `llama3.1:8b` as the default model and pinned release versions for Python,
  Terraform, the Docker provider, and the Ollama image.
- Loopback-only API publishing, private Ollama networking, and model retention
  across routine teardown.
- Unit tests and documented deployment smoke checks.
- README, architecture, project-scope, setup, operation, and teardown
  documentation, plus repository ignore rules for local and generated files.
