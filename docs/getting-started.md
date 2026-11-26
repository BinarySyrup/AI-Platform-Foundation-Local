# Getting Started

Use this guide to start the Local AI Platform Foundation, connect to its API,
and stop the Docker services. The platform runs on your computer through
Terraform and Docker. The RAG containers and API routes are implemented;
capacity and retrieval settings still need target-host measurement and
calibration before uploads and grounded chat are enabled.

## Prerequisites

- Windows is the primary validation host, with Docker Desktop configured for
  WSL2 and Linux containers. Other host operating systems are unverified.
- Terraform CLI `1.17.0` is installed.
- Python `3.14` is optional. You only need it to run tests and code checks; the API runs inside its Docker image.
- Target an 8-core modern x86-64 CPU (AVX2 preferred), 32 GiB RAM, and an SSD.
  Configure Docker Desktop/WSL2 to make about 24 GiB of RAM available to
  Docker. Keep at least 50 GB free in Docker's
  data location before downloading images and models. Treat 10 GB free after
  setup as a provisional planning target, not a validated minimum or ongoing
  reserve. The initial release relies on manual host free-space monitoring;
  benchmark peak temporary use and Qdrant growth to set the ongoing reserve.
  This profile is a target for validation, not a verified minimum. Validate
  CPU-only first. An NVIDIA GPU is optional for Ollama and requires a separate validation run;
  Docling Serve uses its CPU image.
- You do not need an account, password, or API key.

Check Docker and Terraform from PowerShell:

```powershell
terraform -v
docker version
```

Terraform should report version `1.17.0`. Docker should show both **Client** and **Server** versions; if it cannot reach the server, start Docker Desktop. If you plan to run tests, check Python separately:

```powershell
python --version
```

It should report version `3.14.x`.

The API and chat page have no sign-in protection. They are published on localhost and intended for local use.

## Local Installation

From the project folder, prepare Terraform, check the configuration, and review its plan:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Read the plan before continuing. If it looks right, create the services:

```powershell
terraform -chdir=infra/terraform apply
```

Download the default model once:

```powershell
docker exec ollama ollama pull llama3.1:8b
docker exec ollama ollama pull nomic-embed-text:v1.5
```

Terraform builds the API image `local-ai-platform-api:1.3.0` and downloads
Open WebUI `openwebui/open-webui:0.13.4`, Ollama `ollama/ollama:0.40.16`,
Docling Serve CPU `ghcr.io/docling-project/docling-serve-cpu:v1.38.2` and
Qdrant `qdrant/qdrant:v1.20.2`; Terraform pins their linux/amd64 manifest
digests. Record the resolved digests for both Ollama models during setup.

To pull the Open WebUI image manually, run:

```powershell
docker pull openwebui/open-webui:0.13.4
```

The example settings provision the services and direct-chat path. The initial
`rag_max_indexed_chunks` cap is a provisional 25,000; measure Qdrant growth and
adjust it for the target host. RAG chat starts with a provisional
`rag_score_threshold` of `0.50`; tune it after separate retrieval calibration.
To change ports, image tags, model, or data volume names, copy
`infra/terraform/terraform.tfvars.example` to
`infra/terraform/terraform.tfvars` and edit that copy. Git ignores the local
`terraform.tfvars` file.

### Optional NVIDIA GPU

The default is CPU-only. To request all GPUs, set `nvidia_visible_devices = "all"` in your local `infra/terraform/terraform.tfvars` file. You can also set specific device IDs, such as `"0"` or `"0,1"`. Terraform then requests those GPUs for the Ollama container and sets `NVIDIA_VISIBLE_DEVICES` to the same value.

GPU use requires an NVIDIA driver and Docker support for NVIDIA GPUs on the host. Leave the setting empty on a CPU-only host.

## Environment Variables

The API reads settings from its process environment. `.env.example` is a reference list; the app does not load that file by itself. Terraform sets the API's container values. The host bind address is `127.0.0.1` for local runs and `0.0.0.0` inside Docker; Docker still publishes the service only on `127.0.0.1` on your computer.

| Variable | Default | What it changes |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Where the API finds Ollama on the private Docker network. |
| `DEFAULT_MODEL` | `llama3.1:8b` | Model used when a request does not name one. |
| `API_HOST` | `127.0.0.1` locally; `0.0.0.0` in Docker | Address the API listens on. |
| `API_PORT` | `8000` | Port used by the API. |
| `LOG_LEVEL` | `INFO` | How much detail the API writes to its logs. |
| `REQUEST_TIMEOUT_SECONDS` | `120` | How long the API waits for Ollama. |
| `DOCLING_BASE_URL` | `http://docling:5001` | Internal Docling Serve address. |
| `QDRANT_BASE_URL` | `http://qdrant:6333` | Internal Qdrant address. |
| `RAG_COLLECTION_NAME` | `platform_documents` | Qdrant collection name. |
| `RAG_INGESTION_TIMEOUT_SECONDS` | `120` | Full upload and indexing deadline. |
| `RAG_MAX_INDEXED_CHUNKS` | `25000` (provisional) | Logical chunk cap; adjust after measuring Qdrant growth on the target host. |
| `RAG_MAX_PDF_PAGES` | Unset | Optional practical page limit after host validation. |
| `RAG_SCORE_THRESHOLD` | `0.50` (provisional) | Recalibrate against the separate answerable/unanswerable set. |

Terraform passes these values as the API process environment. Settings from
the process environment override application defaults. `.env.example` is a
reference file and is not loaded automatically.

The initial retrieval defaults are page-aware, structure-preserving chunks
targeting 600 lexical token-like units with 100 units of overlap, vector-only
search, and the top 5 results. The lexical counter approximates model tokens.
Use `search_document:` for chunks and `search_query:` for questions. Compare
the paired prefixes with raw text on a separate small synthetic set of
answerable and unanswerable questions; do not tune the threshold against the
held-out quality test.

The collection schema uses the embedding model's default 768-dimensional
vectors and Qdrant Cosine distance, without dimension truncation. Changing the
input convention requires re-embedding the Qdrant collection.

After development, run the held-out quality check with 30 questions across
6 to 10 synthetic PDFs (20 answerable and 10 unanswerable). The acceptance
criteria are at least 18 correct, evidence-grounded answers, correct source
and page for every citation, and no unsupported answers to the 10 unanswerable
questions.

The synthetic held-out corpus and runner are in `docs/evaluation/` and
`scripts/rag_quality_eval.py`. Once RAG is ready and retrieval calibration has
selected the threshold, run:

```powershell
.venv\Scripts\python.exe scripts\rag_quality_eval.py --model llama3.1:8b --output rag-quality-results.json
```

The runner creates and uploads six synthetic, two-page PDFs, then saves all 30
responses and their citations. These documents remain in Qdrant after the run;
delete the returned document IDs through the document API when finished. Review
the answers and fill in each result's `grading` fields in the output file. Then
check the acceptance criteria with:

```powershell
.venv\Scripts\python.exe scripts\rag_quality_eval.py --grade rag-quality-results.json
```

Do not tune retrieval settings against this held-out quality set. Use the
separate calibration examples for threshold selection.

The RAG collection has a configurable `RAG_MAX_INDEXED_CHUNKS` limit, exposed
through the Terraform variable `rag_max_indexed_chunks`. Its initial default
is 25,000 chunks, a provisional value to be checked against target-host storage
measurements. This caps logical indexed chunks; it does not cap all Docker
disk usage.

Terraform also sets these Open WebUI container values:

| Variable | Value | What it does |
| :--- | :--- | :--- |
| `ENABLE_OLLAMA_API` | `false` | Stops Open WebUI from connecting directly to Ollama. |
| `ENABLE_OPENAI_API` | `true` | Enables Open WebUI's connection to the platform API. |
| `OPENAI_API_BASE_URLS` | `http://api:8000/v1` | Connects Open WebUI to the API on the Docker network. |
| `OPENAI_API_KEYS` | `local-development` | Placeholder key; the platform API ignores it. |
| `WEBUI_AUTH` | `false` | Turns off sign-in for this local setup. |

## Running the Application

Open WebUI at <http://127.0.0.1:3000>. The API is at <http://127.0.0.1:8000>. Check that the API is running and can see a model:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/v1/models
```

Check RAG readiness separately:

```powershell
curl.exe http://127.0.0.1:8000/health/rag
```

The endpoint returns HTTP 200 with `ready` when recovery and RAG dependencies
are ready; it returns HTTP 503 while recovery is running or a dependency is
unavailable. RAG operations return HTTP 503 until then. `/health` continues to
report API liveness independently, so direct chat can still work if Ollama is
available.

Other local apps can call the API too:

- `GET /v1/models` lists models in OpenAI-compatible format.
- `POST /v1/chat/completions` sends a normal or streaming chat request.
- `GET /api/v1/models` and `POST /api/v1/chat` use the platform's own API format.
- <http://127.0.0.1:8000/docs> opens the interactive API guide.

The RAG API provides PDF upload, document listing/deletion, retrieval search,
and native RAG chat. Open WebUI shows direct and RAG entries for installed chat
models. A RAG entry retrieves passages from Qdrant before calling the same
Ollama model; the embedding model is omitted from chat choices.

The upload route accepts PDF files up to 1 GB (1,000,000,000 bytes)
and waits synchronously for ingestion. The 120-second configurable deadline
covers file transfer through completed indexing. Only one upload can run at a
time; a concurrent upload receives HTTP 429 immediately. A 1 GB file may
still exceed the deadline, so the practical page limit will be set after
resource and timing validation.

### Managing RAG Documents

Manage documents through Swagger UI at <http://127.0.0.1:8000/docs> or with
`curl.exe`. In Swagger UI, use
**Try it out** on `POST /api/v1/knowledge/documents` and select a PDF file. Use
the returned document ID to delete it; list documents with
`GET /api/v1/knowledge/documents`. Open WebUI remains the chat client and does
not provide the document-management controls.

Upload a synthetic, non-sensitive PDF from PowerShell:

```powershell
curl.exe --max-time 130 -F "file=@C:\path\to\sample.pdf;type=application/pdf" http://127.0.0.1:8000/api/v1/knowledge/documents
```

List indexed documents:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/knowledge/documents
```

Delete a document using the `document_id` returned by upload or listing:

```powershell
curl.exe -X DELETE http://127.0.0.1:8000/api/v1/knowledge/documents/PASTE_DOCUMENT_ID
```

Stop the containers without deleting their data:

```powershell
docker stop local-ai-platform-open-webui local-ai-platform-api ollama
docker stop local-ai-platform-docling local-ai-platform-qdrant
```

Start them again in this order:

```powershell
docker start ollama
docker start local-ai-platform-qdrant local-ai-platform-docling
docker start local-ai-platform-api
docker start local-ai-platform-open-webui
```

`terraform destroy` removes the containers and networks but keeps the model
and Open WebUI data volumes. The RAG deployment also preserves the
Qdrant volume containing indexed chunks and vectors. See the [Terraform
guide](../infra/terraform/README.md) before permanently deleting retained data.
Uploaded PDFs are processed temporarily and are not retained after ingestion.
Keep source PDFs outside the platform if you may need to rebuild the index; if
the Qdrant index is lost or deleted, upload the source PDFs again. Routine
document deletion removes the indexed content from Qdrant and leaves your
external source files unchanged. The initial release does not create Qdrant
snapshots; the Qdrant volume persists across routine teardown but does not
protect against volume loss.

## Running Tests & Linters

This section is optional. Only follow it if you want to run tests or code checks locally. From the project folder, make a Python environment, install the development tools, and run the checks:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

## Common Troubleshooting

- **No models are listed:** Run `docker exec ollama ollama pull llama3.1:8b`, then check `/v1/models` again.
- **The API does not respond:** Make sure Docker Desktop is running, then check `docker logs --tail 100 local-ai-platform-api`.
- **Open WebUI cannot connect:** Check `curl.exe http://127.0.0.1:8000/health`, then check `docker logs --tail 100 local-ai-platform-open-webui`.
- **A port is already in use:** Set `api_host_port` or `open_webui_host_port` in your local `infra/terraform/terraform.tfvars` file.

The `/health` route checks that the API is running; it does not check whether Ollama has finished loading a model or whether RAG dependencies are ready. After RAG is implemented, use `/health/rag` for RAG readiness. See the [architecture guide](architecture.md), [Terraform guide](../infra/terraform/README.md), and [Platform API guide](../platform/README.md) for more details.
