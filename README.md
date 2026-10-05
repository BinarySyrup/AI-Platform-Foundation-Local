# AI Platform Foundation — Local

A portfolio project for designing, provisioning, and operating a small local AI
platform with open-source technologies.

## Project goals

- Keep workloads and data on infrastructure the operator controls.
- Make setup and teardown repeatable and document operational choices.
- Separate infrastructure provisioning from platform configuration.
- Treat credentials, model files, and other local state as sensitive or
  reproducible data—not source code.

## Repository layout

| Path | Purpose |
| --- | --- |
| `docs/` | Architecture notes and project decisions |
| `infra/terraform/` | Terraform infrastructure configuration |
| `platform/` | Platform services and deployment configuration |
| `scripts/` | Repeatable local workflows and helper scripts |

These directories are initial boundaries, not a claim that deployment tooling
has already been selected or implemented. See `docs/architecture.md` for the
current decisions and open questions.

## Getting started

This repository is currently a documentation and structure baseline; it does
not yet provision infrastructure or start services. Before adding a runnable
environment, decide which local host/runtime to target and document its
prerequisites and verification steps here.

## Safety

- Do not commit credentials, private keys, local `.env` files, Terraform state,
  or unreviewed Terraform variable files.
- Review infrastructure plans and service exposure before applying or starting
  them.
- Keep persistent model and application data separate from disposable runtime
  configuration.
