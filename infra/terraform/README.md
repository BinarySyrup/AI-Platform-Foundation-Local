# Terraform Deployment

This configuration uses Terraform 1.16.5 and the Docker provider 4.6.0 to build
the FastAPI image and manage a local Docker network, API container, Ollama
container, and persistent model volume. Ollama uses the pinned
`ollama/ollama:0.35.1` image and is not published on a host port. Only the API is
published, bound to `127.0.0.1`.

Terraform uses local state in this directory. State, provider data, plans, and
environment-specific variable files are excluded from version control. Copy
`terraform.tfvars.example` to `terraform.tfvars` only when you need local
overrides; the copy is ignored by Git.

## Provision

Prerequisites are Terraform 1.16.5 and a running Docker Engine. From the
repository root, initialize and validate the configuration, then review the
plan before applying it:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

Terraform builds the API image from `platform/Dockerfile`; `.dockerignore`
excludes local configuration, Terraform state, model data, and development
artifacts from the build context. The apply output `api_url` points to the
loopback-only API endpoint.

## Prepare and Verify Ollama

The Ollama container is named `ollama` and stores model files in the named
volume reported by `terraform output ollama_volume_name`. Pull the reference
model explicitly after the container starts:

```powershell
docker exec ollama ollama pull llama3.1:8b
```

Record the resolved digest shown by `docker exec ollama ollama list` in the
setup notes when capturing environment details.

Model downloads are intentionally not part of Terraform apply. Verify the API
and available model list with:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/api/v1/models
```

Ollama is reachable by the API at `http://ollama:11434` on the private Docker
bridge network and is not exposed to the host.

## Teardown and Retention

Routine teardown removes the network and containers but retains model data:

```powershell
terraform -chdir=infra/terraform destroy
```

The Ollama container mounts a named Docker volume that is not managed as a
Terraform resource. Docker preserves volume data when the container is removed,
and a later apply reuses the same volume name. To permanently remove models,
first destroy the platform, confirm the volume name with `docker volume ls`,
then explicitly delete the retained volume:

```powershell
docker volume rm local-ai-platform-ollama-models
```

Do not run that cleanup command unless permanent model deletion is intended.
