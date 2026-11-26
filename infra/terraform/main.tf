locals {
  repository_root = abspath("${path.module}/../..")
  api_source_files = sort(concat(
    [".dockerignore", "pyproject.toml", "platform/Dockerfile"],
    [
      for source_file in fileset("${local.repository_root}/platform/app", "**") :
      "platform/app/${source_file}"
    ],
  ))
  api_source_hash = sha256(join("", [
    for source_file in local.api_source_files :
    "${source_file}:${filesha256("${local.repository_root}/${source_file}")}"
  ]))
}

resource "docker_network" "platform" {
  name   = var.platform_network_name
  driver = "bridge"
}

resource "docker_network" "clients" {
  name   = "${var.platform_network_name}-clients"
  driver = "bridge"
}

resource "docker_network" "rag" {
  name   = "${var.platform_network_name}-rag"
  driver = "bridge"
}

resource "docker_image" "api" {
  name = var.api_image_name

  build {
    context    = local.repository_root
    dockerfile = "platform/Dockerfile"
  }

  triggers = {
    source_hash = local.api_source_hash
  }
}

resource "docker_image" "ollama" {
  name         = var.ollama_image
  keep_locally = false
}

resource "docker_image" "open_webui" {
  name = var.open_webui_image
}

resource "docker_image" "docling" {
  name = var.docling_image
}

resource "docker_image" "qdrant" {
  name = var.qdrant_image
}

resource "docker_container" "ollama" {
  name    = "ollama"
  image   = docker_image.ollama.image_id
  restart = "unless-stopped"
  env = var.nvidia_visible_devices == "" ? [] : [
    "NVIDIA_VISIBLE_DEVICES=${var.nvidia_visible_devices}",
  ]
  gpus = var.nvidia_visible_devices == "" ? null : (
    var.nvidia_visible_devices == "all" ? "all" : "device=${var.nvidia_visible_devices}"
  )

  networks_advanced {
    name    = docker_network.platform.name
    aliases = ["ollama"]
  }

  mounts {
    type   = "volume"
    source = var.ollama_volume_name
    target = "/root/.ollama"
  }
}

resource "docker_container" "api" {
  name    = "local-ai-platform-api"
  image   = docker_image.api.image_id
  restart = "unless-stopped"

  env = concat(
    [
      "API_HOST=0.0.0.0",
      "API_PORT=8000",
      "DEFAULT_MODEL=${var.default_model}",
      "LOG_LEVEL=${var.log_level}",
      "OLLAMA_BASE_URL=http://ollama:11434",
      "REQUEST_TIMEOUT_SECONDS=${var.request_timeout_seconds}",
      "DOCLING_BASE_URL=http://docling:5001",
      "QDRANT_BASE_URL=http://qdrant:6333",
      "RAG_COLLECTION_NAME=${var.rag_collection_name}",
      "RAG_INGESTION_TIMEOUT_SECONDS=${var.rag_ingestion_timeout_seconds}",
    ],
    var.rag_max_indexed_chunks == null ? [] : [
      format("RAG_MAX_INDEXED_CHUNKS=%.0f", var.rag_max_indexed_chunks),
    ],
    var.rag_score_threshold == null ? [] : [
      "RAG_SCORE_THRESHOLD=${var.rag_score_threshold}",
    ],
    var.rag_max_pdf_pages == null ? [] : [
      format("RAG_MAX_PDF_PAGES=%.0f", var.rag_max_pdf_pages),
    ],
  )

  ports {
    internal = 8000
    external = var.api_host_port
    ip       = "127.0.0.1"
    protocol = "tcp"
  }

  networks_advanced {
    name    = docker_network.platform.name
    aliases = ["api"]
  }

  networks_advanced {
    name    = docker_network.clients.name
    aliases = ["api"]
  }

  networks_advanced {
    name    = docker_network.rag.name
    aliases = ["api"]
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
    interval     = "30s"
    timeout      = "5s"
    retries      = 3
    start_period = "10s"
  }

  depends_on = [
    docker_container.ollama,
    docker_container.docling,
    docker_container.qdrant,
  ]
}

resource "docker_container" "docling" {
  name    = "local-ai-platform-docling"
  image   = docker_image.docling.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.rag.name
    aliases = ["docling"]
  }
}

resource "docker_container" "qdrant" {
  name    = "local-ai-platform-qdrant"
  image   = docker_image.qdrant.image_id
  restart = "unless-stopped"

  networks_advanced {
    name    = docker_network.rag.name
    aliases = ["qdrant"]
  }

  mounts {
    type   = "volume"
    source = var.qdrant_volume_name
    target = "/qdrant/storage"
  }
}

resource "docker_container" "open_webui" {
  name    = "local-ai-platform-open-webui"
  image   = docker_image.open_webui.image_id
  restart = "unless-stopped"

  env = [
    "ENABLE_OLLAMA_API=false",
    "ENABLE_OPENAI_API=true",
    "OPENAI_API_BASE_URLS=http://api:8000/v1",
    "OPENAI_API_KEYS=local-development",
    "WEBUI_AUTH=false",
  ]

  ports {
    internal = 8080
    external = var.open_webui_host_port
    ip       = "127.0.0.1"
    protocol = "tcp"
  }

  networks_advanced {
    name    = docker_network.clients.name
    aliases = ["open-webui"]
  }

  mounts {
    type   = "volume"
    source = var.open_webui_volume_name
    target = "/app/backend/data"
  }

  depends_on = [docker_container.api]
}
