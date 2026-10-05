# Platform API

This directory contains the FastAPI application, its Ollama adapter, and the
API container image. Terraform deployment resources remain in
`infra/terraform/` and have not been implemented yet.

## Local Development

Use Python 3.14 only and install the pinned development dependencies from the
repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
python -m app.run
```

The local process binds to `127.0.0.1`. `OLLAMA_BASE_URL` must point to an
Ollama instance reachable from the host. In the container deployment, the
default is `http://ollama:11434` on the internal Docker network. The root
`.env.example` is a reference template; Pydantic settings reads process
environment variables and does not load that file automatically.

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

Integration tests require a running Ollama service with the reference model
installed. Set `RUN_OLLAMA_INTEGRATION=1` and configure `OLLAMA_BASE_URL` before
running `python -m pytest -m integration`.

Build the API image from the repository root:

```powershell
docker build -f platform/Dockerfile -t local-ai-platform-api:0.1.0 .
```

The image listens on port 8000 inside its container. Publish the host port on
`127.0.0.1` only and keep Ollama on the internal Docker network.
