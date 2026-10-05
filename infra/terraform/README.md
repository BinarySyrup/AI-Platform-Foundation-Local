# Terraform

Terraform configuration using the Docker provider belongs here. It provisions
the local Docker network, FastAPI and Ollama containers, port mappings, and
persistent model storage. Keep environment-specific values and state out of
version control; the repository root `.gitignore` excludes Terraform state and
variable files.

Pin the required Terraform and provider versions in configuration before adding
resources. Document the state strategy and plan/apply workflow. Ensure routine
service teardown preserves the model volume, and review every plan before
applying it.
