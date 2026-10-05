# Local AI Platform Foundation — Project Scope

## 1. Overview

The Local AI Platform Foundation is a portfolio project demonstrating the provisioning and operation of a small, local AI platform using open-source technologies.

The minimum viable product (MVP) uses Terraform to provision local Docker resources and a Python/FastAPI service to provide access to locally hosted language models through Ollama.

The project prioritizes a clean, reproducible platform foundation over feature breadth. Capabilities such as retrieval-augmented generation (RAG), authentication, vector storage, advanced observability, and Kubernetes deployment are reserved for future phases.

The project demonstrates practical skills in infrastructure as code, container platforms, API design, AI runtime integration, automated testing, and architectural documentation.

## 2. Objectives

The MVP will:

- Provision a local AI runtime and supporting infrastructure using Terraform.
- Run platform components in Docker containers.
- Host locally executable, open-source language models through Ollama.
- Expose a versioned platform API using Python and FastAPI.
- Maintain a clear boundary between the platform API and the model runtime.
- Provide repeatable setup, operation, and teardown workflows.
- Persist downloaded model artifacts independently of container lifecycle.
- Include unit tests and real integration tests where practical.
- Document architecture, implementation decisions, configuration, and operation.
- Establish an extensible foundation for future AI platform capabilities.

## 3. Scope Boundaries

### 3.1 In Scope

The MVP includes:

- Terraform-managed Docker infrastructure.
- A Docker network for internal service communication.
- Containerized FastAPI and Ollama services.
- Persistent storage for Ollama model artifacts.
- Health, model-listing, and non-streaming chat endpoints.
- Request validation and normalized API responses.
- Runtime error handling and configurable request timeouts.
- Basic request logging and correlation identifiers.
- Environment-based application configuration.
- Automated unit and integration testing.
- Local setup, model preparation, operation, and cleanup documentation.

### 3.2 Out of Scope

The MVP excludes:

- Cloud deployment.
- Kubernetes.
- A web frontend.
- User authentication and multi-user access control.
- Retrieval-augmented generation.
- Vector databases.
- Document ingestion.
- Agent workflows.
- Model training or fine-tuning.
- Conversation history and application data persistence.
- Production-grade high availability.
- Healthcare data or protected health information (PHI).

### 3.3 Data and Compliance Boundary

The MVP must use synthetic or non-sensitive data only. Sensitive, proprietary, regulated, or personally identifiable information must not be included in source code, test fixtures, example requests, or project documentation.

Security-conscious architecture does not establish regulatory compliance. The MVP must not be represented as HIPAA-compliant or suitable for regulated workloads.

## 4. Technology Stack

| Area | Technologies | Purpose |
|---|---|---|
| Infrastructure | Terraform, Terraform Docker provider | Define and provision local infrastructure |
| Container runtime | Docker Engine | Run platform services |
| Networking and storage | Docker networks and volumes | Provide internal connectivity and persistent model storage |
| Platform API | Python 3.14, FastAPI, Pydantic, Uvicorn | Expose and validate the platform API |
| Runtime integration | HTTPX | Communicate with Ollama over HTTP |
| Model runtime | Ollama | Manage model artifacts and execute local inference |
| Testing | Pytest, HTTPX test client, Docker-based integration tests | Validate application behavior and runtime integration |
| Code quality | Ruff | Lint and format Python code |
| Optional type checking | MyPy or Pyright | Provide additional static validation |

Runtime and development dependency versions are pinned in the root
`pyproject.toml`; the API supports Python 3.14 only.

Ollama is the initial runtime because it provides a straightforward local execution environment and HTTP API. Runtime-specific integration must remain isolated so that alternative runtimes can be evaluated later.

### 4.1 Reference Model and Validation Profile

Use Ollama's explicit `qwen2.5:1.5b` tag as the canonical MVP model for setup
and integration testing. The Ollama Library lists this model at approximately
986 MB and under the Apache 2.0 license ([model page](https://ollama.com/library/qwen2.5:1.5b)).
Do not use a floating `latest` tag. Record the resolved model digest when the
setup workflow is implemented; keep the model configurable for local overrides.

The initial CPU-only validation target is an x86-64 host with 8 GiB of RAM and
at least 10 GiB of free disk space. This is a target profile, not a verified
minimum requirement. Validate it during implementation and record the tested
host OS, CPU, memory, free disk, and measured peak resource use before claiming
it as supported.

## 5. High-Level Architecture

```text
┌────────────────────────────┐
│ API Client                 │
│ curl / Python / tests      │
└──────────────┬─────────────┘
               │ HTTP
               ▼
┌────────────────────────────┐
│ FastAPI Platform API       │
│ Validation and API contract│
└──────────────┬─────────────┘
               │ Runtime adapter / HTTP
               ▼
┌────────────────────────────┐
│ Ollama                     │
│ Local model execution      │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ Persistent Docker Volume   │
│ Local model artifacts      │
└────────────────────────────┘
```

Terraform provisions the Docker network, containers, port mappings, persistent storage, and infrastructure-level configuration.

### 5.1 Request Flow

1. A client submits a request to the FastAPI service.
2. FastAPI validates the request against the platform schema.
3. The runtime adapter translates the request into the Ollama contract.
4. Ollama executes inference using an available local model.
5. The adapter translates the runtime response into the platform response schema.
6. FastAPI returns the response and records basic request metadata.

Clients interact with the platform API rather than depending directly on Ollama-specific interfaces.

## 6. Component Responsibilities

### 6.1 Terraform

Terraform is responsible for:

- Creating the Docker network.
- Provisioning the Ollama and FastAPI containers.
- Assigning the Ollama container the stable name `ollama` for model preparation.
- Provisioning persistent model storage.
- Configuring service connectivity and required port mappings.
- Defining container restart behavior.
- Applying infrastructure configuration through documented variables.

Terraform must not contain application logic or prompt-processing logic.

The storage lifecycle must distinguish routine service teardown from explicit deletion of model artifacts.

### 6.2 FastAPI Platform API

The platform API is responsible for:

- Exposing the external API contract.
- Validating incoming requests.
- Routing inference requests through a runtime client or adapter.
- Returning normalized responses.
- Handling runtime connectivity failures and timeouts.
- Providing health information.
- Recording basic request logs and correlation identifiers.

Ollama-specific payloads and transport details must remain within the runtime integration layer.

### 6.3 Ollama

Ollama is responsible for:

- Managing local model artifacts.
- Loading and running local models.
- Processing generation requests.
- Providing the internal runtime HTTP API.

Ollama remains an implementation detail behind the platform API.

## 7. Initial API Scope

### 7.1 API Landing Page

```http
GET /
```

**Purpose:** Return a simple HTML landing page showing the current API version.
The displayed version comes from FastAPI's application version metadata.

```html
<html><body><h1>AI Platform Foundation - API</h1><div>API Version:0.1.0</div></body></html>
```

### 7.2 Health

```http
GET /health
```

**Purpose:** Confirm that the FastAPI application is running.

This is a liveness check and does not call Ollama. A successful response is:

```json
{"status":"ok"}
```

### 7.3 List Models

```http
GET /api/v1/models
```

**Purpose:** Return models available in the local runtime.

The response contains model names only, avoiding runtime-specific metadata:

```json
{"models":[{"name":"qwen2.5:1.5b"}]}
```

### 7.4 Chat Completion

```http
POST /api/v1/chat
```

**Purpose:** Submit a conversational request to a selected local model and return a generated response.

Conceptual request:

```json
{
  "model": "qwen2.5:1.5b",
  "messages": [
    {
      "role": "user",
      "content": "Explain infrastructure as code."
    }
  ],
  "options": {
    "temperature": 0.2
  }
}
```

The MVP supports non-streaming responses. The implemented request and response
schemas are published through FastAPI's generated OpenAPI specification.

The implemented request contract accepts 1–100 messages with roles `system`,
`user`, or `assistant`; message content must be non-blank and no longer than
32,000 characters. `model` is optional and defaults to `DEFAULT_MODEL`. The
only supported option is `temperature`, between 0 and 2.

Successful responses use the normalized form:

```json
{
  "model": "qwen2.5:1.5b",
  "message": {"role":"assistant","content":"..."}
}
```

Errors use an `error` object containing a stable `code` and safe `message`, plus
a `request_id`. Validation responses may include field-level details. The API
maps invalid requests to 422, unavailable models to 404, runtime timeouts to
504, runtime connectivity failures to 503, invalid upstream responses to 502,
and unexpected failures to 500. Every response includes an `X-Request-ID`
header. Request logs include method, path, status, duration, and request ID, but
never request or response content.

Expected error scenarios include:

- Invalid request data.
- An unavailable or unknown model.
- An unreachable model runtime.
- An inference request exceeding the configured timeout.
- An unexpected runtime failure.

## 8. Configuration

Application configuration will be supplied through environment variables and documented in `.env.example`.

| Variable | Purpose |
|---|---|
| `OLLAMA_BASE_URL` | Internal HTTP address of the Ollama service |
| `DEFAULT_MODEL` | Default model identifier; `qwen2.5:1.5b` for the MVP |
| `API_HOST` | Application bind address; local process defaults to `127.0.0.1`, while the container sets `0.0.0.0` and relies on loopback-only host port publishing |
| `API_PORT` | Application listening port |
| `LOG_LEVEL` | Application logging verbosity |
| `REQUEST_TIMEOUT_SECONDS` | Timeout for runtime requests |

The application reads process environment variables directly. `.env.example`
is documentation only and is not loaded automatically.

Infrastructure configuration will use Terraform variables, with example values documented in `infra/terraform/terraform.tfvars.example`.

Configuration loading and precedence must be documented; `.env.example` is a reference template, not an automatically loaded configuration mechanism.

Secrets are not expected in the MVP. If introduced later, they must not be committed to the repository.

## 9. Persistence and Data Lifecycle

The MVP requires persistent storage for Ollama model artifacts.

Model data must survive:

- Container restarts.
- Routine Terraform re-application.
- FastAPI image rebuilds and container replacement.
- Routine platform service teardown.

Model artifacts must be deleted only through a documented, explicit cleanup process.

The Terraform storage design must support this lifecycle. A volume managed in the same Terraform state as the services is ordinarily subject to `terraform destroy`; preservation must therefore be implemented deliberately rather than assumed.

Conversation history, user records, and application state persistence are outside the MVP scope.

## 10. Security and Operational Constraints

The platform is intended for local development and portfolio demonstration, not deployment as a publicly accessible service.

The MVP must:

- Bind the published FastAPI port explicitly to `127.0.0.1`; do not publish
  Ollama's API to the host by default.
- Keep Ollama accessible through the internal Docker network unless direct access is explicitly needed for development.
- Avoid logging prompt and response content by default.
- Use synthetic or non-sensitive inputs.
- Exclude local configuration, Terraform state, and generated artifacts from version control as appropriate.
- Document resource requirements and expected limitations.

Authentication is out of scope. The platform must not rely on the absence of authentication being acceptable beyond its local-only deployment boundary.

Inference latency and supported model size depend on available CPU, memory, storage, and optional GPU capability. No production throughput or availability commitment is included in this scope.

## 11. Repository Structure

```text
AI-Platform-Foundation-Local/
├── AGENTS.md
├── CHANGELOG.md
├── README.md
├── LICENSE
├── Makefile
├── pyproject.toml
├── .gitignore
├── .env.example
├── docker-compose.yml          # Optional developer convenience
│
├── platform/
│   ├── README.md
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── api/
│       ├── clients/
│       ├── models/
│       ├── services/
│       └── settings.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── infra/
│   └── terraform/
│       ├── README.md
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── versions.tf
│       └── terraform.tfvars.example
│
├── scripts/
│   └── README.md
└── docs/
    ├── project-scope.md
    ├── architecture.md
    ├── getting-started.md
    └── decisions/
```

Terraform remains the primary provisioning mechanism. If Docker Compose is included, its purpose and resource ownership must be documented to avoid conflicting management of the same containers, networks, or volumes.

## 12. Operational Workflow

### 12.1 Prerequisites

The setup documentation must identify:

- Supported local environment.
- Required Docker, Terraform, and Python versions.
- Application image build steps.
- The reference validation profile: CPU-only x86-64, 8 GiB RAM, and at least
  10 GiB free disk; record actual test results before treating it as verified.
- Network access required to download dependencies, images, and model artifacts.

### 12.2 Provision Infrastructure

From the repository root:

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

### 12.3 Prepare a Model

After the Ollama container starts, download the canonical test model:

```bash
docker exec ollama ollama pull qwen2.5:1.5b
```

The Ollama container must have the stable name `ollama` for this command. Model
download orchestration does not need to be implemented as Terraform application
logic. Record the resolved model digest during setup; local overrides may use
another installed model.

### 12.4 Verify the Platform

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/models
```

Then submit a chat request to `POST /api/v1/chat` using an installed model.

### 12.5 Teardown and Cleanup

The documented routine teardown must remove service resources while preserving model artifacts.

Where services are managed in the primary Terraform configuration, the teardown command is:

```bash
terraform -chdir=infra/terraform destroy
```

Before this workflow is considered complete, the storage implementation must ensure that routine destruction does not delete model data.

A separate, explicit cleanup procedure must describe how to permanently remove retained model artifacts.

## 13. Testing and Quality

### 13.1 Unit Tests

Unit tests should cover:

- Request validation.
- Platform-to-runtime request translation.
- Runtime-to-platform response normalization.
- Configuration handling.
- Error and timeout mapping.

### 13.2 Integration Tests

Docker-based integration tests must verify:

- FastAPI-to-Ollama connectivity.
- Model listing against a running runtime.
- Successful chat generation using an installed model.

Tests should validate response structure and successful generation rather than exact generated text.

Runtime unavailability and timeout handling should also be tested where practical.

### 13.3 Quality Checks

The project must provide documented commands for:

- Running unit tests.
- Running integration tests.
- Linting and formatting with Ruff.
- Validating Terraform configuration.

Static type checking with MyPy or Pyright is optional for the MVP.

## 14. Deliverables

The MVP will deliver:

1. Terraform configuration for the local Docker platform.
2. A containerized FastAPI application.
3. An isolated Ollama integration layer.
4. Persistent model storage with documented retention and deletion behavior.
5. Health, model-listing, and chat endpoints.
6. Unit and integration test suites.
7. Configuration examples and repeatable developer commands.
8. Setup, operation, testing, and teardown documentation.
9. Architecture documentation and records of significant design decisions.

## 15. MVP Acceptance Criteria

The MVP is complete when:

- [ ] Terraform initializes and validates successfully.
- [ ] Terraform provisions the required Docker resources.
- [ ] FastAPI and Ollama containers start successfully.
- [ ] FastAPI communicates with Ollama over the internal network.
- [ ] The health endpoint returns the documented response.
- [ ] The models endpoint lists the canonical `qwen2.5:1.5b` model.
- [ ] The resolved reference-model digest is recorded in setup documentation.
- [ ] The chat endpoint generates a response from the canonical model.
- [ ] Invalid requests and runtime failures produce documented API errors.
- [ ] Model data persists across container restarts and routine re-provisioning.
- [ ] Routine service teardown preserves model artifacts.
- [ ] Explicit model-data deletion is documented.
- [ ] Unit tests are included and pass.
- [ ] Integration tests validate real FastAPI-to-Ollama communication.
- [ ] Required linting and validation checks pass.
- [ ] The README documents setup, model preparation, execution, testing, and teardown.
- [ ] Architecture and significant design decisions are documented.
- [ ] No sensitive or proprietary data is included.
- [ ] FastAPI's published host port binds only to `127.0.0.1`; Ollama has no
      published host port by default.
- [ ] The reference validation profile is tested and its measured resource use
      is documented.

## 16. Key Risks and Dependencies

| Risk or dependency | Impact | Mitigation |
|---|---|---|
| Insufficient local compute or memory | Slow inference or model load failures | Validate with a small model and document tested hardware |
| Large model downloads | Longer setup times and increased disk usage | Document download sizes and persist model artifacts |
| Runtime API changes | Integration failures | Isolate the runtime adapter and document tested versions |
| Destructive storage lifecycle | Loss of downloaded models | Separate retention from routine teardown and verify cleanup behavior |
| Nondeterministic model output | Brittle automated tests | Assert response structure and meaningful output, not exact wording |
| Terraform and Compose ownership overlap | Conflicting infrastructure state | Keep Terraform primary and clearly separate optional Compose workflows |

## 17. Future Enhancements

Potential future phases include:

- Expanded model management and configuration.
- Streaming responses.
- Request and response metrics.
- OpenTelemetry tracing.
- Structured audit logging.
- PostgreSQL metadata storage.
- Document ingestion.
- Vector search with Qdrant.
- RAG workflows.
- Authentication with Keycloak.
- Kubernetes deployment.
- Azure and AWS infrastructure.
- CI/CD automation and Terraform security scanning.

These capabilities are not MVP commitments. Each should be introduced only after its requirements, operational cost, security implications, and architectural impact have been evaluated.

## 18. Project Positioning

This project demonstrates:

- Infrastructure as code with Terraform.
- Local container platform provisioning.
- Python API development and FastAPI service design.
- Local language model execution.
- API integration with an AI runtime.
- Persistent model storage.
- Automated testing.
- Reproducible operational workflows.
- Architecture and decision documentation.
- A foundation for future AI platform capabilities.

### Portfolio Summary

> I built a reproducible local AI platform foundation using Terraform, Docker, Python, FastAPI, and Ollama, with a clean API boundary between platform services and locally hosted language models.
