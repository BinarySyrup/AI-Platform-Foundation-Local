# ADR 0001: Local PDF RAG Architecture

- **Status:** Accepted
- **Date:** 2026-11-23
- **Updated:** 2026-11-24 (PDF retention, ingestion limits, validation profile, readiness, index recovery, and retrieval baseline)

## Context

The platform already provides Open WebUI, a FastAPI boundary, and local Ollama
chat models. The project is expanding its release scope to answer questions
using locally indexed PDF documents while keeping document processing,
embeddings, retrieval, and generation on the Docker host.

The design must let the user keep selecting an existing Ollama generation
model, preserve the direct-chat path, avoid a custom frontend, and return
traceable source references. The primary validation host is Windows with
Docker Desktop, WSL2, and Linux containers; other host operating systems remain
unverified. The target machine has a modern 8-core x86-64 CPU (AVX2 preferred),
32 GiB RAM with about 24 GiB available to Docker, and SSD storage with 50 GB
free before setup and at least 10 GB free afterward. CPU-only is the baseline;
NVIDIA GPU setups are validated separately. The profile is not yet verified
for Docling conversion and Ollama inference running together.

## Decisions

### RAG is in the local release scope

The release includes local PDF ingestion, vector retrieval, and grounded chat.
Cloud parsing, hosted embeddings, and hosted vector storage are excluded. The
platform continues to use synthetic or non-sensitive data only.

### Keep the platform API as the orchestration boundary

FastAPI owns document upload, extraction orchestration, chunking, embeddings,
indexing, retrieval, model routing, and response formatting. Open WebUI and
other clients call FastAPI. They do not call Ollama, Docling Serve, or Qdrant
directly.

### Offer direct and RAG choices for each supported chat model

The OpenAI-compatible model list contains a direct entry and a RAG alias for
each supported Ollama chat model. The RAG alias is a FastAPI routing identifier
such as `llama3.1:8b-rag`, not another model file. FastAPI resolves the alias to
the underlying selected generation model before calling Ollama. Direct entries
keep their existing no-retrieval behavior. This uses Open WebUI's model picker
instead of adding a custom UI control.

The embedding model is excluded from the chat model list.

### Use one fixed local embedding model

Ollama runs `nomic-embed-text:v1.5` to embed both document chunks and user
queries. The selected chat model remains responsible for generation. Record
the embedding model's resolved digest during setup. A collection uses one
embedding model and vector schema; changing either requires rebuilding the
index from the source PDFs.

### Use Qdrant for local vector storage

Qdrant runs in its own Docker container and stores vectors, chunk text, and
source metadata in a persistent named volume. FastAPI owns collection setup,
upsert, search, and document deletion. Routine Terraform teardown preserves
the Qdrant volume; permanent removal is an explicit cleanup action. The initial
release does not create or manage Qdrant snapshots. If the index is lost or
deleted, users rebuild it by re-uploading their externally retained PDFs.
Volume persistence protects against routine teardown, not volume loss.

### Keep original PDFs outside the platform

FastAPI processes uploaded PDFs transiently and does not retain the original
files after ingestion. Users keep their source PDFs outside the platform so
they can rebuild the index if needed. Temporary upload and conversion files
must be removed after successful processing and on failure paths. Qdrant
continues to persist extracted chunk text, vectors, and source metadata until
the document is deleted or the Qdrant volume is explicitly removed. The
initial release has no Qdrant snapshot or restore workflow; recovery from
index loss is to recreate the index and upload the source PDFs again. This
accepts reprocessing time in exchange for a simpler local deployment.

### Use the official Docling Serve CPU container for PDF conversion

Run the upstream `ghcr.io/docling-project/docling-serve-cpu` image separately
from the FastAPI image. FastAPI sends PDF file uploads to its conversion API and
preserves returned source and page metadata. The parser has no host port and
does not communicate directly with Ollama or Qdrant. Do not use Docling Serve's
URL-based conversion endpoint.

The image is selected as a technology, not yet pinned to a specific release
and immutable digest. Those values must be chosen and recorded before
deployment. Qdrant also requires a pinned version and digest.

### Keep the initial ingestion format to PDF

The first ingestion release accepts PDF uploads up to 1 GB (1,000,000,000
bytes). Upload and indexing are synchronous with a configurable
`RAG_INGESTION_TIMEOUT_SECONDS` deadline, defaulting to 120 seconds for the full
request from file transfer through completed indexing. Only one upload may
process at a time; another concurrent attempt is rejected immediately with
HTTP 429 and is not queued. FastAPI streams the upload to temporary storage
rather than buffering the full file in memory. It creates a unique temporary
directory in the API container's writable filesystem, not a persistent volume,
and removes it during normal cleanup. At API startup, it deletes leftover
upload directories from an earlier process before enabling RAG ingestion.
Qdrant chunk points begin in a `pending` state; RAG search and document listing
expose only `ready` documents. After all points are indexed, FastAPI marks the
document ready. At startup, it finds document IDs with any pending points and
deletes all points for those documents before enabling RAG operations. This
also removes a document if a crash interrupts publishing its ready state.
Scanned-PDF OCR is deferred until resource use and page-level
citation quality are validated on the reference host. Other document formats
are outside this release.

The initial deployment runs one API container and one worker. Startup cleanup
assumes there is no concurrent ingestion in another API process; a future
multi-worker deployment must coordinate cleanup with active uploads.

The 1 GB value is a hard file-size ceiling, not a guarantee that every file
under that size will finish within 120 seconds. Establish a practical page-count
limit and verify the size, memory, and timing limits on the target host before
release.

### Make identical PDF uploads idempotent

FastAPI calculates SHA-256 while streaming the PDF and uses the digest as the
stable document identity. The first successful upload indexes the document and
returns HTTP 201. An upload with the exact same bytes returns HTTP 200 with the
existing document metadata and does not parse or index it again. The filename
from the first successful upload remains the canonical display and citation
name. A file with the same filename but different bytes is a new document; it
does not replace the existing one. Failed or timed-out indexing removes partial
Qdrant points so a retry can start cleanly.

### Keep RAG semantics explicit

The RAG entry uses the latest user message for retrieval and adds relevant,
source-labelled passages as untrusted context. If no passages meet the
configured relevance threshold, it reports that the documents do not provide
enough information. It does not silently fall back to general model knowledge.
If Docling Serve, Ollama embeddings, or Qdrant is unavailable, the RAG request
returns an error instead of bypassing retrieval. The direct entry remains
available for general questions.

RAG answers provide human-readable PDF and page citations when page metadata is
available. The platform-native response also exposes structured source
metadata. Streaming and non-streaming RAG requests use the same retrieval and
citation rules.

### Start with page-aware vector retrieval

Chunk Docling's extracted structure at paragraph and heading boundaries while
keeping chunks within their source PDF page. Target 600 tokens per chunk with
100 tokens of overlap, preserving page metadata for citations. Start with
vector-only retrieval and return the top 5 chunks. Hybrid search and reranking
are outside the initial release. These are starting values and must be
validated with synthetic PDFs; changing chunk size or overlap requires
rebuilding the Qdrant index.

Set `RAG_SCORE_THRESHOLD` through evaluation before release rather than picking
an arbitrary score. The synthetic evaluation set must include answerable and
unanswerable questions. Check whether retrieval returns the expected content
and page, and whether weak or absent matches produce the no-support response.

### Separate API liveness from RAG readiness

Keep `GET /health` as a liveness check that does not depend on RAG services.
Add `GET /health/rag` with an overall `starting`, `ready`, or `unavailable`
status and dependency status. RAG readiness requires startup cleanup to finish
and Qdrant, Docling Serve, and the Ollama embedding model to be available. The
endpoint returns HTTP 200 only in the ready state and HTTP 503 otherwise. RAG
routes return HTTP 503 until ready. Direct chat remains available when Ollama
is available, even if RAG is starting or unavailable. The API continues to
serve liveness and direct chat while startup recovery runs.

### Isolate internal services and preserve data

Terraform provisions a client network, an Ollama runtime network, and a RAG
network. FastAPI joins all three; Open WebUI joins only the client network;
Ollama joins only the runtime network; Docling Serve and Qdrant join only the
RAG network. Docling Serve and Qdrant have no published host ports.

Qdrant persists extracted chunks, vectors, and source metadata. Original PDFs
are processed transiently and are not retained after ingestion; users keep
their source files outside the platform for re-indexing. Temporary upload and
conversion files must be removed after processing, including failure paths.
The initial release does not provide Qdrant backup snapshots; users recover a
lost index by re-uploading their externally retained PDFs. Persistence of the
named volume protects against routine teardown only. Use explicit file-size,
page-count, timeout, and concurrency limits. Do not log document content,
prompts, retrieved passages, or generated responses by default.

## Alternatives Considered

### Apache Tika

Tika provides broad file-format extraction and is suitable for straightforward
text extraction. Docling was selected because its structured PDF output better
supports page-aware chunking, tables, and citations for this RAG use case.

### Docling as a library inside the FastAPI image

This would avoid an internal HTTP hop, but would place Docling's large parsing
and model dependencies in the API image and share its process lifecycle and
resource limits. A separate container keeps the API image and parser lifecycle
independent.

### Third-party `hwdsl2/docling-server` / ParseCrate image

This image packages Docling Serve with additional setup and management
conveniences. The upstream Docling Serve CPU image was selected to avoid an
extra wrapper layer and keep the parser closer to the project that maintains
the API. The upstream image still requires an explicit release and digest pin.

### A RAG toggle or custom frontend

A separate UI toggle would require Open WebUI customization or another client
integration. Paired model entries use Open WebUI's existing model selection
and let the user choose direct or RAG behavior per conversation.

### Using the selected chat model for embeddings

Generation models are not a consistent embedding interface. A fixed dedicated
embedding model gives documents and queries compatible vectors, independent of
which generation model the user chooses.

## Consequences

### Benefits

- Users can choose direct or document-grounded behavior per conversation while
  reusing their downloaded Ollama chat models.
- PDF parsing, vector search, embeddings, and generation stay local.
- Page metadata and source references support traceable answers.
- The API remains the single client-facing boundary.
- Parser, vector store, and runtime dependencies can be versioned and operated
  independently.

### Costs and risks

- Docling Serve and Qdrant add images, networks, health checks, and persistent
  data to the local deployment.
- The Docling CPU image is several gigabytes and may compete with Ollama for
  memory, CPU, and temporary disk. Validate the 32 GiB / 50 GB target profile
  during ingestion and inference before claiming it is supported.
- Embedding-model changes require reindexing the collection.
- Losing the Qdrant volume requires users to re-upload their externally kept
  source PDFs to rebuild the index.
- PDF structure and page boundaries must survive parsing and chunking for
  useful citations.
- Retrieved text can contain prompt-injection instructions and must be treated
  as untrusted context.
- The RAG model list contains API aliases in addition to real Ollama models;
  FastAPI must keep their mappings explicit and collision-safe.

## Implementation Gates

- Pin the official Docling Serve CPU image and Qdrant to explicit releases and
  immutable digests.
- Verify temporary upload and conversion files are removed after success and
  failure; verify partial Qdrant points are rolled back on errors and timeout.
- Validate the 1 GB file-size boundary, the 120-second configurable deadline,
  immediate rejection of a second upload, and a practical page-count limit on
  the target host.
- Validate parser page limits, PDF citations, and conversion behavior.
- Document and validate index recovery by creating a fresh Qdrant collection
  and re-uploading synthetic source PDFs after index loss.
- On the primary CPU-only host, test the default `llama3.1:8b` model, fixed
  embedding model, Docling Serve, and Qdrant together. Ingest a representative
  synthetic PDF at the practical page limit while issuing a chat request;
  verify completion within 120 seconds without exhausting memory or disk and
  record peak resource use and chat latency.
- Measure image storage and peak disk/RAM use during concurrent parsing and
  model inference on the target host. Validate NVIDIA GPU setups separately.
- Update `.env.example` and Terraform examples when the implementation adds
  the corresponding runtime configuration.
- Add unit tests for parsing, upload limits, SHA-256 duplicate detection and
  idempotent retries, timeout/cancellation cleanup, concurrent-upload rejection,
  chunking, embeddings, vector operations,
  routing, no-match responses, and dependency failures, plus a Docker
  deployment check using a synthetic PDF.
