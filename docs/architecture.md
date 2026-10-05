# Architecture

## Intent

Build a small, local-first AI platform that can be provisioned and operated
repeatably. The design should favor understandable components, explicit
configuration, and safe defaults over production-scale complexity.

## Initial boundaries

- **Infrastructure:** Terraform configuration belongs in `infra/terraform/`.
- **Platform:** service definitions and platform configuration belong in
  `platform/`.
- **Automation:** repeatable operator workflows belong in `scripts/`.
- **Documentation:** decisions, setup steps, and operational guidance belong in
  `docs/` and the relevant directory README.

These boundaries do not prescribe a Terraform provider, container runtime,
orchestration system, model runtime, or user interface.

## Decisions to make before implementation

1. Choose the supported host and infrastructure target (for example, one local
   workstation versus a separate homelab host).
2. Choose the runtime and deployment mechanism, including how services will be
   reached from the host.
3. Choose the model-serving and user-interface components based on hardware,
   licensing, and maintenance needs.
4. Define persistent storage, backup expectations, and which data is disposable.
5. Define network exposure and secret handling; default to local-only access
   until a deliberate alternative is documented.
6. Add a smoke test that verifies the deployed service without requiring a
   specific model or sending data externally.

## Operational principles

- Pin tool and image versions once the stack is selected.
- Keep generated state and credentials out of version control.
- Make setup, health checks, upgrades, and teardown explicit and repeatable.
- Document hardware assumptions, resource requirements, and known limitations.
