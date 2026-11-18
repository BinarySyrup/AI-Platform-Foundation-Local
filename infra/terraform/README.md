# Terraform Deployment

This configuration uses Terraform 1.17.0 and the Docker provider 4.6.0 to build
the FastAPI image and manage Open WebUI, Ollama, two Docker networks, and
persistent data volumes. Open WebUI uses the pinned
`openwebui/open-webui:0.13.4` image, and Ollama uses the pinned
`ollama/ollama:0.40.16` image. The API shares a client network
with Open WebUI and a separate runtime network with Ollama, so the UI reaches
the model through the API. The API and Open WebUI are published on loopback;
Ollama has no host port.

Terraform uses local state in this directory. State, provider data, plans, and
environment-specific variable files are excluded from version control. Copy
`terraform.tfvars.example` to `terraform.tfvars` only when you need local
overrides; the copy is ignored by Git.

## Provision

Prerequisites are Terraform 1.17.0 and a running Docker Engine. From the
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
artifacts from the build context. The apply outputs `api_url` and
`open_webui_url` point to the loopback-only services.

## Optional NVIDIA GPU

GPU access is disabled by default. Leave `nvidia_visible_devices` empty for a
CPU-only Docker host. To request all GPUs, set it to `"all"` in your local
`terraform.tfvars`; to select devices, use IDs such as `"0"` or `"0,1"`.
Terraform passes the selection both as Docker GPU devices and as
`NVIDIA_VISIBLE_DEVICES` in the Ollama container.

List the NVIDIA GPU IDs visible to the host with:

```powershell
nvidia-smi --query-gpu=index,name,uuid --format=csv,noheader
```

Use the index values from the output for `nvidia_visible_devices`. If the
command is not found or lists no GPUs, leave the setting empty for CPU-only
operation.

The host needs an NVIDIA driver and Docker support for NVIDIA GPUs. The setting
does not install host drivers or NVIDIA Container Toolkit.

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
curl.exe http://127.0.0.1:8000/v1/models
```

Open the chat interface at `http://127.0.0.1:3000`. It calls the API at
`http://api:8000/v1` on the private client network. The placeholder API key in
the Open WebUI configuration is ignored by the unauthenticated platform API;
the services are safe to use only within the local loopback boundary.

Ollama is reachable by the API at `http://ollama:11434` on the private Docker
bridge network and is not exposed to the host.

## Teardown and Retention

Routine teardown removes the networks, containers, and Terraform-managed Docker
images. It retains model data in the Ollama volume and chats/settings in the
Open WebUI volume:

```powershell
terraform -chdir=infra/terraform destroy
```

Both containers mount named Docker volumes that are not managed as Terraform
resources. Docker preserves their contents when containers are removed, and a
later apply reuses the configured names. To permanently remove either set of
data, first destroy the platform and confirm the relevant volume name with
`docker volume ls`. To permanently remove model artifacts, use:

```powershell
docker volume rm local-ai-platform-ollama-models
```

To permanently remove Open WebUI conversations and settings, use:

```powershell
docker volume rm local-ai-platform-open-webui-data
```

Run the Ollama command only when permanent model deletion is intended. Run the
Open WebUI command only when permanent conversation and settings deletion is
intended.

If the Ollama image remains cached after teardown, confirm no other container
uses it before removing it:

```powershell
docker image ls ollama/ollama:0.40.16
docker image rm ollama/ollama:0.40.16
```

Do not use `--force`; Docker should refuse removal if a container still uses
the image. Removing the image does not delete models stored in the volume.
