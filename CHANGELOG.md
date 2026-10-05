# Changelog

Notable project changes are documented here.

## [Unreleased]

### Added

- Defined the local AI platform MVP around Terraform, Docker, FastAPI, and Ollama.
- Added architecture and project-scope documentation, plus guidance for agents
  and the infrastructure, platform, and scripts directories.
- Added a FastAPI application with an Ollama adapter, validated API schemas,
  normalized errors, request IDs, and unit/integration tests.
- Added a root HTML endpoint that reports the current API version.

### Changed

- Expanded the README with project goals, repository layout, and safety guidance.
- Extended `.gitignore` for local secrets, Terraform plans and state, Python
  artifacts, local model data, and IDE files.
- Aligned the scope, README, architecture, and Terraform guidance on the selected
  stack and repository paths; specified loopback-only API publishing and a
  pinned reference model/profile.
