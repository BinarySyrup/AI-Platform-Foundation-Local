# Architecture

## Intent

Build a small, local-first AI platform that can be provisioned and operated
repeatably. The design should favor understandable components, explicit
configuration, and safe defaults over production-scale complexity.

## Selected MVP

- **Infrastructure:** Terraform with the Docker provider, in `infra/terraform/`.
- **Container runtime:** Docker Engine.
- **Platform API:** Python/FastAPI in `platform/`.
- **Model runtime:** Ollama, reachable by the API over an internal Docker
  network.
- **Host access:** publish the API on `127.0.0.1` only by default; do not publish
  Ollama's API to the host.
- **Automation and docs:** repeatable workflows belong in `scripts/`; project
  documentation belongs in `docs/` and the relevant directory README.

The MVP does not include a UI, authentication, cloud deployment, or
orchestration beyond Docker.

## Decisions to finalize before implementation

1. Specify supported host platforms and pin Terraform, provider, Docker image,
   Python, and Ollama versions.
2. Implement model-volume retention so routine Terraform teardown preserves
   model data, with a separate explicit cleanup operation.
3. Document configuration loading and precedence, including `.env.example`.
4. Define liveness/readiness responses and startup behavior when Ollama is
   unavailable.
5. Validate the reference hardware profile and record measured resource use.
6. Add smoke and integration tests using the pinned reference model, without
   sending prompts or model data externally.

## Operational principles

- Pin tool, provider, image, and model versions before implementation is treated
  as reproducible.
- Keep generated state and credentials out of version control.
- Make setup, health checks, upgrades, and teardown explicit and repeatable.
- Document hardware assumptions, resource requirements, and known limitations.
