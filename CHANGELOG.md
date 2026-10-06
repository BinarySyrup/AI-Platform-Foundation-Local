# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
