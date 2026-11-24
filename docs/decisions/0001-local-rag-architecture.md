# ADR 0001: Local PDF RAG Architecture

- **Status:** Accepted
- **Date:** 2026-11-23

## Context

The platform already provides Open WebUI, a FastAPI boundary, and local Ollama
chat models. The project is expanding its release scope to answer questions
using locally indexed PDF documents while keeping document processing,
embeddings, retrieval, and generation on the Docker host.

The design must let the user keep selecting an existing Ollama generation
model, preserve the direct-chat path, avoid a custom frontend, and return
traceable source references. The reference host is CPU-only x86-64 with 8 GiB
RAM and 10 GiB free disk, but that resource profile is not yet verified for
Docling conversion and Ollama inference running together.

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
the Qdrant volume; permanent removal is an explicit cleanup action.

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

The first ingestion release accepts bounded PDF uploads. FastAPI chunks
Docling's structured extraction output and embeds each chunk through Ollama.
Scanned-PDF OCR is deferred until resource usage and page-level citation
quality are validated on the reference host. Other document formats are
outside this release.

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

### Isolate internal services and preserve data

Terraform provisions a client network, an Ollama runtime network, and a RAG
network. FastAPI joins all three; Open WebUI joins only the client network;
Ollama joins only the runtime network; Docling Serve and Qdrant join only the
RAG network. Docling Serve and Qdrant have no published host ports.

Qdrant persists extracted chunks, vectors, and source metadata. The proposed
default is to process source PDFs transiently and require users to keep their
own files for re-indexing; this retention policy must be confirmed before
implementation. Use explicit file-size, page-count, timeout, and concurrency
limits. Do not log document content, prompts, retrieved passages, or generated
responses by default.

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
  memory and CPU. The existing 8 GiB RAM / 10 GiB free disk target may need to
  change after measurement.
- Embedding-model changes require reindexing the collection.
- PDF structure and page boundaries must survive parsing and chunking for
  useful citations.
- Retrieved text can contain prompt-injection instructions and must be treated
  as untrusted context.
- The RAG model list contains API aliases in addition to real Ollama models;
  FastAPI must keep their mappings explicit and collision-safe.

## Implementation Gates

- Pin the official Docling Serve CPU image and Qdrant to explicit releases and
  immutable digests.
- Confirm whether uploaded source PDFs are transient or retained by the
  platform; the proposed default is transient processing.
- Validate parser file/page limits, timeout behavior, PDF citations, and
  conversion concurrency.
- Measure image storage and peak disk/RAM use during concurrent parsing and
  model inference on the reference host.
- Update `.env.example` and Terraform examples when the implementation adds
  the corresponding runtime configuration.
- Add unit tests for parsing, chunking, embeddings, vector operations, routing,
  no-match responses, and dependency failures, plus a Docker deployment check
  using a synthetic PDF.
