# Getting Started

Use this guide to start the Local AI Platform Foundation, connect to its API, and stop the Docker services. The platform runs on your computer through Terraform and Docker.

## Prerequisites

- Docker Desktop is installed and running with Linux containers.
- Terraform CLI `1.17.0` is installed.
- Python `3.14` is optional. You only need it to run tests and code checks; the API runs inside its Docker image.
- You do not need an account, password, or API key.

Check Docker and Terraform from PowerShell:

```powershell
terraform -v
docker version
```

Terraform should report version `1.17.0`. Docker should show both **Client** and **Server** versions; if it cannot reach the server, start Docker Desktop. If you plan to run tests, check Python separately:

```powershell
python --version
```

It should report version `3.14.x`.

The API and chat page have no sign-in protection. They are published on localhost and intended for local use.

## Local Installation

From the project folder, prepare Terraform, check the configuration, and review its plan:

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Read the plan before continuing. If it looks right, create the services:

```powershell
terraform -chdir=infra/terraform apply
```

Download the default model once:

```powershell
docker exec ollama ollama pull llama3.1:8b
```

Terraform builds the API image `local-ai-platform-api:1.2.0` and downloads Open WebUI `openwebui/open-webui:0.13.4` and Ollama `ollama/ollama:0.40.16`.

To pull the Open WebUI image manually, run:

```powershell
docker pull openwebui/open-webui:0.13.4
```

The example settings already work. To change ports, image tags, model, or data volume names, copy `infra/terraform/terraform.tfvars.example` to `infra/terraform/terraform.tfvars` and edit that copy. Git ignores the local `terraform.tfvars` file.

### Optional NVIDIA GPU

The default is CPU-only. To request all GPUs, set `nvidia_visible_devices = "all"` in your local `infra/terraform/terraform.tfvars` file. You can also set specific device IDs, such as `"0"` or `"0,1"`. Terraform then requests those GPUs for the Ollama container and sets `NVIDIA_VISIBLE_DEVICES` to the same value.

GPU use requires an NVIDIA driver and Docker support for NVIDIA GPUs on the host. Leave the setting empty on a CPU-only host.

## Environment Variables

The API reads settings from its process environment. `.env.example` is a reference list; the app does not load that file by itself. Terraform sets the API's container values. The host bind address is `127.0.0.1` for local runs and `0.0.0.0` inside Docker; Docker still publishes the service only on `127.0.0.1` on your computer.

| Variable | Default | What it changes |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Where the API finds Ollama on the private Docker network. |
| `DEFAULT_MODEL` | `llama3.1:8b` | Model used when a request does not name one. |
| `API_HOST` | `127.0.0.1` locally; `0.0.0.0` in Docker | Address the API listens on. |
| `API_PORT` | `8000` | Port used by the API. |
| `LOG_LEVEL` | `INFO` | How much detail the API writes to its logs. |
| `REQUEST_TIMEOUT_SECONDS` | `120` | How long the API waits for Ollama. |

Terraform also sets these Open WebUI container values:

| Variable | Value | What it does |
| :--- | :--- | :--- |
| `ENABLE_OLLAMA_API` | `false` | Stops Open WebUI from connecting directly to Ollama. |
| `ENABLE_OPENAI_API` | `true` | Enables Open WebUI's connection to the platform API. |
| `OPENAI_API_BASE_URLS` | `http://api:8000/v1` | Connects Open WebUI to the API on the Docker network. |
| `OPENAI_API_KEYS` | `local-development` | Placeholder key; the platform API ignores it. |
| `WEBUI_AUTH` | `false` | Turns off sign-in for this local setup. |

## Running the Application

Open WebUI at <http://127.0.0.1:3000>. The API is at <http://127.0.0.1:8000>. Check that the API is running and can see a model:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/v1/models
```

Other local apps can call the API too:

- `GET /v1/models` lists models in OpenAI-compatible format.
- `POST /v1/chat/completions` sends a normal or streaming chat request.
- `GET /api/v1/models` and `POST /api/v1/chat` use the platform's own API format.
- <http://127.0.0.1:8000/docs> opens the interactive API guide.

Stop the containers without deleting their data:

```powershell
docker stop local-ai-platform-open-webui local-ai-platform-api ollama
```

Start them again in this order:

```powershell
docker start ollama
docker start local-ai-platform-api
docker start local-ai-platform-open-webui
```

`terraform destroy` removes the containers and networks but keeps the model and Open WebUI data volumes. See the [Terraform guide](../infra/terraform/README.md) before permanently deleting either volume.

## Running Tests & Linters

This section is optional. Only follow it if you want to run tests or code checks locally. From the project folder, make a Python environment, install the development tools, and run the checks:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

## Common Troubleshooting

- **No models are listed:** Run `docker exec ollama ollama pull llama3.1:8b`, then check `/v1/models` again.
- **The API does not respond:** Make sure Docker Desktop is running, then check `docker logs --tail 100 local-ai-platform-api`.
- **Open WebUI cannot connect:** Check `curl.exe http://127.0.0.1:8000/health`, then check `docker logs --tail 100 local-ai-platform-open-webui`.
- **A port is already in use:** Set `api_host_port` or `open_webui_host_port` in your local `infra/terraform/terraform.tfvars` file.

The `/health` route checks that the API is running; it does not check whether Ollama has finished loading a model. See the [architecture guide](architecture.md), [Terraform guide](../infra/terraform/README.md), and [Platform API guide](../platform/README.md) for more details.
