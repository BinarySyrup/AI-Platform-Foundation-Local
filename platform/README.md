# Platform

The FastAPI service, its Dockerfile, and platform configuration belong here.
Keep deployment configuration separate from infrastructure provisioning in
`infra/terraform/`; the selected model runtime is Ollama.

Follow `docs/project-scope.md` for the reference model, localhost-only host port
binding, persistent model data, and health-check requirements. Pin service
versions and document upgrade/rollback procedures. Do not commit credentials or
generated model data.
