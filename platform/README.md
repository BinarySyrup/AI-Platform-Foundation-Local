# Platform API

This directory contains the FastAPI application, its Ollama adapter, and the
API container image. Terraform in `infra/terraform/` builds the image and runs
the API beside Ollama on a private Docker network.

## Docker Deployment

The API is intended to run in the Terraform-managed Docker environment, not as
a host process connected to a local Ollama server. It reaches Ollama at
`http://ollama:11434` on the private Docker network. The API is published on
`127.0.0.1:8000` by the Terraform configuration.

## API

- `GET /` returns an HTML landing page with the current API version.
- `GET /health` reports API liveness without calling Ollama.
- `GET /api/v1/models` returns model names only.
- `POST /api/v1/chat` accepts 1–100 non-blank messages with `system`, `user`, or
  `assistant` roles. `model` is optional and defaults to `DEFAULT_MODEL`;
  `options.temperature` is optional and must be between 0 and 2.
- Interactive OpenAPI documentation is available at `/docs` while the service
  is running.

Errors use a stable JSON envelope and a request ID. The API logs request method,
path, status, duration, and request ID; it does not log prompt or response
content.

## Tests and Container Image

Run unit tests and lint checks from the repository root:

```powershell
python -m pytest tests/unit
python -m ruff check .
python -m ruff format --check .
```

Terraform builds the API image automatically during apply. To build it
manually from the repository root:

```powershell
docker build -f platform/Dockerfile -t local-ai-platform-api:1.0.0 .
```

The image listens on port 8000 inside its container. Publish the host port on
`127.0.0.1` only and keep Ollama on the internal Docker network.
