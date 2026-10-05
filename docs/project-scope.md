Local AI Platform Foundation — Project Scope
1. Overview
   The Local AI Platform Foundation is a portfolio project demonstrating how to provision and operate a small, local AI platform using open-source technologies.

The initial MVP will use Terraform to provision Docker resources locally, with a Python/FastAPI platform API providing access to locally hosted large language models through Ollama.

The project is intentionally starting small. The goal is to establish a clean, reproducible platform foundation before adding capabilities such as retrieval-augmented generation, vector storage, authentication, observability, and Kubernetes.

This project reflects my experience designing cloud platforms, secure APIs, distributed services, Docker-based environments, Terraform workflows, and AI-enabled engineering solutions. 1

2. Goals
   The MVP goals are to:

Provision a local AI runtime using Terraform.
Run platform components in Docker containers.
Host open-source LLMs locally using Ollama.
Provide a Python-based API using FastAPI.
Establish a clean boundary between the platform API and the model runtime.
Provide repeatable local setup and teardown.
Support basic API and integration testing.
Create a foundation that can evolve toward a broader AI platform.
Document architecture, decisions, operation, and future capabilities.
3. Non-Goals
   The initial MVP will not include:

Cloud deployment
Kubernetes
Web frontend
User authentication
Multi-user access control
Retrieval-augmented generation
Vector databases
Document ingestion
Agent workflows
Model fine-tuning
Model training
Production-grade high availability
Healthcare or protected health information
The platform may eventually support regulated workloads, but this MVP must use synthetic or non-sensitive data only. It should not be represented as HIPAA-compliant merely because the architecture includes security-minded design principles.

4. Technology Stack
   Infrastructure
   Terraform
   Terraform Docker provider
   Docker Engine
   Docker volumes
   Docker network
   Terraform will define and manage the local infrastructure resources. Terraform, Docker, and Kubernetes are technologies included in my platform engineering and DevOps background. 2

Platform API
Python
FastAPI
Pydantic
Uvicorn
HTTPX
The FastAPI service will expose a stable API contract and communicate with Ollama over HTTP.

LLM Runtime
Ollama
Locally hosted open-source models
Ollama is the initial model runtime because it provides a simple local execution environment and HTTP API. The platform API should remain sufficiently abstracted so another model runtime can be evaluated later.

Testing and Quality
Pytest
HTTPX test client
Ruff
Optional MyPy or Pyright
Docker-based integration testing
The project should favor real integration tests where practical rather than relying exclusively on mocks.

5. High-Level Architecture
   Text

Copy
┌─────────────────────┐
│  API Client          │
│  curl / Python test  │
└──────────┬──────────┘
│
▼
┌─────────────────────┐
│  FastAPI Platform   │
│  API                 │
└──────────┬──────────┘
│ HTTP
▼
┌─────────────────────┐
│  Ollama              │
│  Local LLM Runtime   │
└──────────┬──────────┘
│
▼
┌─────────────────────┐
│  Local Open-Source  │
│  Language Model      │
└─────────────────────┘
Terraform provisions the Docker network, containers, ports, volumes, and configuration required to run the platform.

6. Component Responsibilities
   Terraform
   Terraform is responsible for:

Creating the Docker network.
Creating the Ollama container.
Creating the FastAPI container.
Creating persistent storage for model data.
Configuring service connectivity.
Exposing required ports.
Defining container restart behavior.
Managing environment-specific configuration.
Terraform will not contain application logic or prompt-processing logic.

FastAPI Platform API
The FastAPI service is responsible for:

Providing the external platform API.
Validating requests.
Forwarding model requests to Ollama.
Returning normalized responses.
Handling runtime errors.
Providing health checks.
Adding basic request logging and correlation identifiers.
The API should not be tightly coupled to Ollama-specific request formats beyond the adapter or client layer.

Ollama
Ollama is responsible for:

Running local language models.
Managing local model artifacts.
Processing generation requests.
Providing the model runtime HTTP API.
Ollama is an implementation detail behind the platform API.

7. Initial API Scope
   The initial API will provide the following endpoints:

Health
Http

Copy
GET /health
Purpose:

Confirm that the FastAPI application is running.
Optionally report whether Ollama is reachable.
List Models
Http

Copy
GET /api/v1/models
Purpose:

Return models available to the local Ollama runtime.
Chat Completion
Http

Copy
POST /api/v1/chat
Purpose:

Submit a conversational request to a selected local model.
Return the generated response.
Example conceptual request:

JSON

Copy
{
"model": "llama3.2",
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
The exact request and response schemas will be defined during implementation.

8. Configuration
   Configuration should be supplied through environment variables and documented in .env.example.

Potential configuration values include:

Text

Copy
OLLAMA_BASE_URL
DEFAULT_MODEL
API_HOST
API_PORT
LOG_LEVEL
REQUEST_TIMEOUT_SECONDS
Secrets are not expected in the initial MVP. If secrets are introduced later, they must not be committed to the repository.

9. Persistence
   The MVP requires persistent storage for Ollama model files.

The model volume should survive:

Container restarts
Terraform re-application
FastAPI container rebuilds
The model volume should be removed only through an explicit cleanup process.

Application state, conversation history, and user data are outside the initial scope.

10. Repository Scope
    The initial repository should contain:

Text

Copy
local-ai-platform/
├── README.md
├── LICENSE
├── Makefile
├── pyproject.toml
├── .env.example
├── docker-compose.yml
│
├── app/
│   ├── main.py
│   ├── api/
│   ├── clients/
│   ├── models/
│   ├── services/
│   └── settings.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
│
└── docs/
├── project-scope.md
├── architecture.md
├── getting-started.md
└── decisions/
Docker Compose may be included as a developer convenience, but Terraform should remain the primary provisioning mechanism for the MVP.

11. Operational Workflow
    The expected workflow is:

Bash

Copy
terraform init
terraform validate
terraform plan
terraform apply
After the platform is running:

Bash

Copy
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/models
The platform should then support a chat request through the FastAPI endpoint.

Cleanup:

Bash

Copy
terraform destroy
The documentation must clearly explain whether model data is preserved or deleted during destruction.

12. MVP Acceptance Criteria
    The MVP is complete when:

Terraform initializes successfully.
Terraform validates successfully.
Terraform provisions the required Docker resources.
The FastAPI container starts successfully.
The Ollama container starts successfully.
FastAPI can communicate with Ollama.
The health endpoint returns successfully.
The models endpoint returns available models.
The chat endpoint generates a response from a local model.
Model data persists across container restarts.
Unit tests are included.
Integration tests cover FastAPI-to-Ollama communication.
The README documents setup, execution, testing, and teardown.
No sensitive or proprietary data is included.
13. Future Enhancements
    Potential future phases include:

Model management and model configuration
Streaming responses
Request and response metrics
OpenTelemetry tracing
Structured audit logging
PostgreSQL metadata storage
Document ingestion
Vector search with Qdrant
RAG workflows
Authentication with Keycloak
Kubernetes deployment
Azure and AWS infrastructure
CI/CD and Terraform security scanning
These enhancements should be introduced based on demonstrated requirements rather than added all at once. My approach to platform architecture is to establish clear boundaries and operational foundations first, similar to the platform governance, cloud migration, API, and documentation work described in my professional background. 3

14. Project Positioning
    This project demonstrates:

Infrastructure as code with Terraform
Local container platform provisioning
Python API development
FastAPI service design
Local LLM execution
API integration with an AI runtime
Persistent model storage
Automated testing
Architecture documentation
A foundation for future AI platform capabilities
The central portfolio message is:

I built a reproducible local AI platform foundation using Terraform, Docker, Python, FastAPI, and Ollama, with a clean API boundary between platform services and locally hosted language models.