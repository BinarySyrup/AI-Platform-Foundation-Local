# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-28

### Added

- Architecture diagram and README guidance for verifying Terraform resources,
  container health, model availability, and API connectivity.

### Changed

- Bump the API and container image to 1.1.0, upgrade Terraform to 1.17.0, and
  update the pinned FastAPI, Pydantic, pytest, and Ruff versions.
- Remove the Terraform-managed Ollama image on destroy while preserving the
  model volume; document cleanup for images retained by earlier destroys.
- Clarify model selection and remove the repository tree from the README.
- Set the Mermaid infrastructure diagram to a top-to-bottom layout.

## [1.0.0] - 2026-10-06

### Added

- Terraform-managed Docker deployment with a private network, FastAPI API and
  Ollama containers, and a persistent model volume.
- Versioned API endpoints for the HTML landing page, health, model listing, and
  non-streaming chat, with validated schemas, normalized errors, and request IDs.
- `llama3.1:8b` as the default model and pinned release versions for Python,
  Terraform, the Docker provider, and the Ollama image.
- Loopback-only API publishing, private Ollama networking, and model retention
  across routine teardown.
- Unit tests and documented deployment smoke checks.
- README, architecture, project-scope, setup, operation, and teardown
  documentation, plus repository ignore rules for local and generated files.
