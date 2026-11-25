# Terraform Deployment

This configuration uses Terraform 1.17.0 and the Docker provider 4.6.0 to build
the FastAPI image and manage Open WebUI, Ollama, Docker networks, and
persistent data volumes. The target RAG deployment adds the official Docling
Serve CPU image `ghcr.io/docling-project/docling-serve-cpu:v1.38.2` and Qdrant image
`qdrant/qdrant:v1.20.2`. Open WebUI uses the pinned
`openwebui/open-webui:0.13.4` image, and Ollama uses the pinned
`ollama/ollama:0.40.16` image. The API shares a client network with Open
WebUI, a runtime network with Ollama, and a RAG network with Docling Serve and
Qdrant. Only FastAPI can reach the runtime and RAG services. The API and Open
WebUI are published on loopback; Ollama, Docling Serve, and Qdrant have no host
ports. RAG Terraform resources are part of the target scope and remain pending
implementation.

Terraform uses local state in this directory. State, provider data, plans, and
environment-specific variable files are excluded from version control. Copy
`terraform.tfvars.example` to `terraform.tfvars` only when you need local
overrides; the copy is ignored by Git.

## Provision

Prerequisites are Terraform 1.17.0 and a running Docker Engine. The primary
validation host is Windows with Docker Desktop, WSL2, and Linux containers. The
target is an 8-core x86-64 CPU, 32 GiB RAM with about 24 GiB available to Docker,
and SSD storage with 50 GB free before setup. Treat 10 GB free after setup as a
provisional planning target, not a validated minimum or ongoing reserve. The
initial release relies on manual host free-space monitoring and does not enforce
a physical free-space threshold. Benchmark peak temporary processing use and
Qdrant growth to establish the ongoing reserve.
Validate CPU-only first; GPU setups are a separate profile. From the repository
root, initialize and validate the configuration, then review the plan before
applying it:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

Terraform builds the API image from `platform/Dockerfile`; `.dockerignore`
excludes local configuration, Terraform state, model data, and development
artifacts from the build context. The apply outputs `api_url` and
`open_webui_url` point to the loopback-only services.

Before RAG deployment is implemented, record the immutable digests for
`ghcr.io/docling-project/docling-serve-cpu:v1.38.2` and
`qdrant/qdrant:v1.20.2`. Do not use floating tags.

## Optional NVIDIA GPU

GPU access is disabled by default. Leave `nvidia_visible_devices` empty for a
CPU-only Docker host. To request all GPUs, set it to `"all"` in your local
`terraform.tfvars`; to select devices, use IDs such as `"0"` or `"0,1"`.
Terraform passes the selection both as Docker GPU devices and as
`NVIDIA_VISIBLE_DEVICES` in the Ollama container.

The host needs an NVIDIA driver and Docker support for NVIDIA GPUs. The setting
does not install host drivers or NVIDIA Container Toolkit.

## Prepare and Verify Ollama

The Ollama container is named `ollama` and stores model files in the named
volume reported by `terraform output ollama_volume_name`. Pull the reference
model explicitly after the container starts:

```powershell
docker exec ollama ollama pull llama3.1:8b
docker exec ollama ollama pull nomic-embed-text:v1.5
```

Record the resolved digests shown by `docker exec ollama ollama list` in the
setup notes when capturing environment details. `nomic-embed-text:v1.5` is the
fixed embedding model for the indexed collection; it is not a chat selection.

Model downloads are intentionally not part of Terraform apply. Verify the API
and available model list with:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/api/v1/models
curl.exe http://127.0.0.1:8000/v1/models
```

Once the RAG API is implemented, verify its separate readiness endpoint with
`curl.exe http://127.0.0.1:8000/health/rag`. A ready response requires startup
recovery to finish and Qdrant, Docling Serve, and the Ollama embedding model to
be available. The endpoint returns HTTP 503 until those conditions are met,
and RAG routes remain unavailable during that time. `/health` reports API
liveness independently; direct chat may work while RAG is unavailable.

Open the chat interface at `http://127.0.0.1:3000`. It calls the API at
`http://api:8000/v1` on the private client network. The placeholder API key in
the Open WebUI configuration is ignored by the unauthenticated platform API;
the services are safe to use only within the local loopback boundary.

Ollama is reachable by the API at `http://ollama:11434` on the private Docker
bridge network and is not exposed to the host.

The target RAG deployment makes Docling Serve and Qdrant reachable only by the
API on a separate private RAG network. The API sends uploaded PDF files to
Docling Serve's file-conversion endpoint and must not use its URL-fetch
endpoint. Synchronous ingestion has a hard 1 GB (1,000,000,000 bytes)
file-size ceiling and a configurable 120-second end-to-end deadline. The
deadline is controlled by `RAG_INGESTION_TIMEOUT_SECONDS` and the planned
Terraform variable `rag_ingestion_timeout_seconds`. One upload runs at a time;
additional uploads are rejected with HTTP 429 rather than queued. The API
streams uploads to per-upload scratch directories in the API container's
writable filesystem, not a named volume. It removes scratch data and partial
index points on all terminal paths, and sweeps abandoned scratch directories
at startup. Startup also deletes all points for documents with pending chunks
before enabling RAG operations. A practical page-count limit remains subject to validation;
the 1 GB ceiling does not guarantee completion within 120 seconds.

The starting retrieval configuration uses page-aware chunks targeting 600
tokens with 100 tokens of overlap, vector-only search, and the top 5 results.
Set the relevance threshold after evaluating synthetic answerable and
unanswerable questions. Use the default 768-dimensional embedding output with
Qdrant Cosine distance and no dimension truncation. Evaluate Nomic task
prefixes (`search_document:` for chunks, `search_query:` for queries) against
unprefixed input and record the selected convention. Chunk-size, overlap, or
prefix changes require rebuilding the Qdrant index.

The planned Terraform variable `rag_max_indexed_chunks` configures the
collection-wide chunk cap and is passed to the API as
`RAG_MAX_INDEXED_CHUNKS`. Set its value from measured Qdrant volume growth on
the target host. The cap bounds logical index size, not physical Docker disk
usage. Monitor host free space manually; benchmark peak temporary conversion
use and Qdrant growth to establish the ongoing reserve.

## Teardown and Retention

Routine teardown removes the networks, containers, and Terraform-managed Docker
images. It retains model data in the Ollama volume, chats/settings in the Open
WebUI volume, and indexed chunks/vectors in the Qdrant volume:

```powershell
terraform -chdir=infra/terraform destroy
```

The Ollama, Open WebUI, and Qdrant containers mount named Docker volumes that
are not managed as Terraform resources. Docker preserves their contents when
containers are removed, and a later apply reuses the configured names. To
permanently remove data, first destroy the platform and confirm the relevant
volume name with `docker volume ls`. To permanently remove model artifacts,
use:

```powershell
docker volume rm local-ai-platform-ollama-models
```

To permanently remove Open WebUI conversations and settings, use:

```powershell
docker volume rm local-ai-platform-open-webui-data
```

To permanently remove indexed document chunks, vectors, and source metadata,
use:

```powershell
docker volume rm local-ai-platform-qdrant-data
```

Run the Ollama command only when permanent model deletion is intended. Run the
Open WebUI command only when permanent conversation and settings deletion is
intended. Run the Qdrant command only when permanent document-index deletion
is intended. This removes indexed chunks, vectors, and metadata. Original PDFs
are processed transiently and are not retained after ingestion; keep source
files outside the platform if you may need to rebuild the index. The initial
release does not create Qdrant snapshots. Rebuilding a deleted or lost index
requires recreating the collection and uploading those source PDFs again. The
Qdrant volume persists across routine teardown but does not protect against
volume loss.

If the Ollama image remains cached after teardown, confirm no other container
uses it before removing it:

```powershell
docker image ls ollama/ollama:0.40.16
docker image rm ollama/ollama:0.40.16
```

Do not use `--force`; Docker should refuse removal if a container still uses
the image. Removing the image does not delete models stored in the volume.
