# Platform

Service definitions and platform configuration belong here. Keep deployment
configuration separate from infrastructure provisioning in `infra/terraform/`.

Before adding services, document the selected runtime, version-pinning policy,
ports and network exposure, persistent data locations, health checks, and
upgrade/rollback procedure. Do not commit credentials or generated model data.
