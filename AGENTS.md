# Agent Instructions

## Project direction

- Read `docs/project-scope.md` before implementing features. It defines the MVP: Terraform with the Docker provider, Docker, a Python/FastAPI platform API, and Ollama.
- Keep the API as the boundary between clients and the model runtime; isolate Ollama-specific behavior behind a client or adapter.
- Keep work within the MVP. Do not add cloud deployment, Kubernetes, authentication, a frontend, RAG, vector storage, document ingestion, agents, or model training unless the scope is deliberately revised.
- Preserve the repository layout documented in `docs/project-scope.md`: `infra/terraform/`, `platform/`, `scripts/`, and `docs/`. Do not move files implicitly.
- Keep `README.md` and `docs/architecture.md` consistent with the selected MVP stack when changing project direction or setup.

## Safety and data

- Use synthetic or non-sensitive data only. Do not claim the project is HIPAA-compliant.
- Keep unauthenticated services bound to localhost by default. Document and review any broader network exposure.
- Never commit credentials, private keys, `.env` files, Terraform state, or real environment-specific `.tfvars` files. Update `.env.example` when adding configuration.
- Treat Ollama model files as persistent data. Do not delete model volumes or other user data without an explicit cleanup request; document retention behavior for Terraform teardown.
- Review Terraform plans before applying them. Avoid destructive defaults and make cleanup behavior explicit.

## Implementation conventions

- Keep changes focused and follow the existing structure and style.
- Pin tool, provider, container-image, and model versions for reproducible setup; avoid floating tags or versions.
- Add or update tests for behavior changes. Use unit tests for API logic and integration tests for FastAPI-to-Ollama behavior where practical.
- Document setup, configuration, health checks, tests, and teardown for any new runnable component.
- Do not add inline code comments unless they clarify non-obvious behavior or are requested.

## Validation

- Run the narrowest relevant tests and checks first, then broader checks when practical.
- For Terraform changes, run `terraform fmt -check`, `terraform validate`, and review `terraform plan` when the required provider and Docker daemon are available.
- For Python changes, run the relevant `pytest` tests and Ruff checks when configured.
- If a check cannot run because prerequisites are unavailable, report that clearly rather than implying it passed.
