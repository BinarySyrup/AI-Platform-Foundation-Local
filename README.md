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

The stack and target architecture are documented, but this repository is still
a documentation baseline: Terraform resources, the FastAPI application, and
tests have not been implemented. The commands below describe the intended
workflow and are not runnable until those components are added.

The initial CPU-only validation target is an x86-64 host with 8 GiB of RAM and
at least 10 GiB of free disk. This is a target profile, not a verified minimum;
record the tested host and measured resource use before claiming support.

## Planned Workflow

### Prerequisites

The implementation must document supported host platforms and pin the required
Terraform, provider, Docker, Python, and Ollama image versions. Docker must be
available to the Terraform Docker provider.

### Provision

Run these commands from the repository root after the Terraform configuration
is implemented:

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

Review the plan before applying. The FastAPI port must be published on
`127.0.0.1` only; Ollama remains on the internal Docker network.

### Prepare and Verify

The reference model is downloaded into the persistent Ollama volume:

```bash
docker exec ollama ollama pull qwen2.5:1.5b
```

Then check the API and installed models:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/models
```

The chat endpoint is `POST /api/v1/chat`. Its final request and response schema
will be defined in the API's OpenAPI documentation; integration tests use the
reference model and validate successful generation without asserting exact
wording.

### Teardown

Routine service teardown uses:

```bash
terraform -chdir=infra/terraform destroy
```

Routine teardown must preserve model artifacts. Permanently deleting the model
volume requires a separate, documented cleanup procedure.

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
