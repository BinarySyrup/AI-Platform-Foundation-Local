# AI Platform Foundation — Local

A local-first AI platform MVP built with Terraform, Docker, FastAPI, and Ollama.
The project demonstrates repeatable infrastructure provisioning and a stable
API boundary around locally hosted language models.

## Tech Stack

| Area | Frameworks |
| --- | --- |
| Infrastructure | Terraform (1.16.5); Docker provider (4.6.0) |
| Container runtime | Docker Engine (host-installed; version not pinned) |
| Platform API | Python (3.14); FastAPI (0.142.2); Pydantic (2.13.5); Uvicorn (0.54.0) |
| Model runtime | Ollama (0.35.1) `ollama/ollama:0.35.1` container image |
| Default model | [`llama3.1:8b`](https://ollama.com/library/llama3.1) |
| Quality | HTTPX (0.28.1); Pytest (9.1.1); Ruff (0.16.10) |

The API exposes health, model-listing, and non-streaming chat endpoints. It
validates requests and normalizes responses; Ollama-specific HTTP details stay
inside the runtime adapter. See [`docs/project-scope.md`](docs/project-scope.md)
for the complete MVP scope and acceptance criteria.

## Project Status

The FastAPI application, Ollama adapter, Terraform Docker resources, and unit
tests are implemented. Terraform builds and runs the API and Ollama containers,
publishes the API on loopback, and retains Ollama model data across routine
teardown. Review the Terraform plan before applying it.

The initial CPU-only validation target is an x86-64 host with 8 GiB of RAM and
at least 10 GiB of free disk. This is a target profile, not a verified minimum;
record the tested host and measured resource use before claiming support.

The API is intended to run as part of the Terraform-managed Docker environment;
it uses `http://ollama:11434` to reach Ollama on the private Docker network.
This project does not support connecting the API to a host-local Ollama server.
After deployment, the API provides `GET /`, `GET /health`,
`GET /api/v1/models`, and `POST /api/v1/chat` on `127.0.0.1:8000`. Interactive
OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

## Tests and API Image

Use Python 3.14 to run unit tests and Ruff checks from the repository root:

```powershell
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

Build the API container image from the repository root:

```powershell
docker build -f platform/Dockerfile -t local-ai-platform-api:1.0.0 .
```

## Deploy the Docker Platform

With Terraform 1.16.5, Docker provider 4.6.0, and Docker Engine available, run
these commands from the repository root. Review the plan before applying it:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

Terraform builds the API image and publishes it on `127.0.0.1:8000`. Ollama is
available only on the internal Docker network. After apply, prepare the
reference model explicitly:

```powershell
docker exec ollama ollama pull llama3.1:8b
```

Verify the API health and model-listing endpoints after the model is ready:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/api/v1/models
```

Send a synthetic chat request to verify model generation:

```powershell
$body = @{
    messages = @(@{ role = "user"; content = "Reply with a short greeting." })
    options = @{ temperature = 0 }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/chat" `
    -ContentType "application/json" `
    -Body $body
```

Routine `terraform destroy` preserves the Ollama model volume. The explicit
volume deletion procedure is documented in [`infra/terraform/README.md`](infra/terraform/README.md).

## Repository Layout

```text
AI-Platform-Foundation-Local/
├── .dockerignore
├── .env.example
├── .gitignore
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture.md
│   └── project-scope.md
├── infra/
│   └── terraform/
│       ├── .terraform.lock.hcl
│       ├── README.md
│       ├── main.tf
│       ├── outputs.tf
│       ├── terraform.tfvars.example
│       ├── variables.tf
│       └── versions.tf
├── platform/
│   ├── Dockerfile
│   ├── README.md
│   └── app/
│       ├── api/
│       ├── clients/
│       ├── models/
│       ├── __init__.py
│       ├── main.py
│       ├── run.py
│       └── settings.py
├── scripts/
│   └── README.md
└── tests/
    ├── unit/
    ├── __init__.py
    └── helpers.py
```

Terraform is the primary provisioning mechanism. Docker Compose, if added, is a
developer convenience and must not manage resources already owned by Terraform.

## Security and Data

- Keep the unauthenticated API bound to localhost; do not publish Ollama's API
  to the host by default.
- Use synthetic or non-sensitive data only. This project is not HIPAA-compliant
  and is not intended for regulated workloads.
- Do not log prompts or responses by default.
- Never commit credentials, private keys, `.env` files, Terraform state, or
  real environment-specific `.tfvars` files.
- Treat model files as persistent data; review Terraform plans and document
  cleanup before deleting them.

## Future Scope

Cloud deployment, Kubernetes, authentication, a frontend, RAG, vector databases,
document ingestion, agent workflows, and model training are intentionally
excluded from the MVP. See [`docs/architecture.md`](docs/architecture.md) for
the selected architecture and remaining implementation decisions.
