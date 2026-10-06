# AI Platform Foundation — Local

A local-first AI platform MVP built with Terraform, Docker, FastAPI, and Ollama.
The project demonstrates repeatable infrastructure provisioning and a stable
API boundary around locally hosted language models.

## MVP Stack

| Area | Selection |
| --- | --- |
| Infrastructure | Terraform with the Docker provider |
| Container runtime | Docker Engine |
| Platform API | Python and FastAPI |
| Model runtime | Ollama |
| Reference model | [`qwen2.5:1.5b`](https://ollama.com/library/qwen2.5:1.5b), Apache 2.0, approximately 986 MB |
| Quality | Pytest, HTTPX, and Ruff |

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

## Run the API Locally

Use Python 3.14 only. From the repository root, install dependencies and run the
service in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
python -m app.run
```

This development setup expects Ollama to be reachable from the host and binds
the API to `127.0.0.1`. The container default instead uses
`http://ollama:11434` over the internal Docker network. `.env.example` lists
configuration variables but is not loaded automatically.

The API provides `GET /` for an HTML page with the current API version,
`GET /health`, `GET /api/v1/models`, and `POST /api/v1/chat`. Interactive
OpenAPI documentation is available at
`http://127.0.0.1:8000/docs`. The request schema and error contract are described
in [`docs/project-scope.md`](docs/project-scope.md).

## Tests and API Image

Run unit tests and Ruff checks from the repository root:

```powershell
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

Integration tests require an Ollama service with `qwen2.5:1.5b` installed. Set
`RUN_OLLAMA_INTEGRATION=1` and `OLLAMA_BASE_URL` to a reachable Ollama API, then
run `python -m pytest -m integration`.

Build the API container image from the repository root:

```powershell
docker build -f platform/Dockerfile -t local-ai-platform-api:beta.1.0.0 .
```

## Provision the Local Platform

With Terraform 1.16.5 and Docker Engine available, run these commands from the
repository root. Review the plan before applying it:

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
docker exec ollama ollama pull qwen2.5:1.5b
```

Routine `terraform destroy` preserves the Ollama model volume. The explicit
volume deletion procedure is documented in [`infra/terraform/README.md`](infra/terraform/README.md).

## Repository Layout

```text
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── LICENSE
├── Makefile
├── pyproject.toml
├── .env.example
├── platform/
│   ├── Dockerfile
│   └── app/
├── tests/
│   ├── unit/
│   └── integration/
├── infra/
│   └── terraform/
├── scripts/
└── docs/
    ├── project-scope.md
    ├── architecture.md
    ├── getting-started.md
    └── decisions/
```

Terraform is the primary provisioning mechanism. Docker Compose, if added, is a
developer convenience and must not manage resources already owned by Terraform.

## Testing and Quality

- Run unit tests with Pytest.
- Run Docker-based integration tests against a real Ollama service.
- Use HTTPX for API tests and Ruff for linting and formatting.
- Run `terraform fmt -check`, `terraform validate`, and review a Terraform plan.
- Test request validation, runtime errors/timeouts, model listing, and chat
  generation with the pinned reference model.

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
