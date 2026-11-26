variable "api_host_port" {
  description = "Loopback host port published for the platform API."
  type        = number
  default     = 8000

  validation {
    condition     = var.api_host_port >= 1 && var.api_host_port <= 65535
    error_message = "api_host_port must be a valid TCP port between 1 and 65535."
  }
}

variable "api_image_name" {
  description = "Tag assigned to the locally built platform API image."
  type        = string
  default     = "local-ai-platform-api:1.3.0"
}

variable "open_webui_host_port" {
  description = "Loopback host port published for Open WebUI."
  type        = number
  default     = 3000

  validation {
    condition     = var.open_webui_host_port >= 1 && var.open_webui_host_port <= 65535
    error_message = "open_webui_host_port must be a valid TCP port between 1 and 65535."
  }
}

variable "open_webui_image" {
  description = "Version-pinned Open WebUI container image."
  type        = string
  default     = "openwebui/open-webui:0.13.4"
}

variable "open_webui_volume_name" {
  description = "Docker volume that retains Open WebUI conversations and settings across destroy."
  type        = string
  default     = "local-ai-platform-open-webui-data"
}

variable "default_model" {
  description = "Default Ollama model requested by the platform API."
  type        = string
  default     = "llama3.1:8b"

  validation {
    condition     = length(trimspace(var.default_model)) > 0
    error_message = "default_model must not be empty."
  }
}

variable "docling_image" {
  description = "Pinned linux/amd64 Docling Serve CPU image and manifest digest."
  type        = string
  default     = "ghcr.io/docling-project/docling-serve-cpu:v1.38.2@sha256:7b31b3c2efa17534dfcffb61665b71bbc959ad309b5b7ed82c3bbdcc63cc3d58"
}

variable "log_level" {
  description = "Application log level passed to the platform API."
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
  }
}

variable "ollama_image" {
  description = "Version-pinned Ollama container image."
  type        = string
  default     = "ollama/ollama:0.40.16"
}

variable "nvidia_visible_devices" {
  description = "Optional NVIDIA devices for Ollama; leave empty for CPU-only Docker hosts."
  type        = string
  default     = ""
}

variable "ollama_volume_name" {
  description = "Docker volume that retains Ollama model artifacts across Terraform destroy."
  type        = string
  default     = "local-ai-platform-ollama-models"
}

variable "platform_network_name" {
  description = "Runtime Docker network for the API and Ollama; a -clients network is created for the API and Open WebUI."
  type        = string
  default     = "local-ai-platform"
}

variable "qdrant_image" {
  description = "Pinned linux/amd64 Qdrant image and manifest digest."
  type        = string
  default     = "qdrant/qdrant:v1.20.2@sha256:c5e32ee251293d2e1f4dd34890ad75eeee5a4f3821a121d6d8b7e4323448b386"
}

variable "qdrant_volume_name" {
  description = "Docker volume that retains indexed document chunks, vectors, and metadata across destroy."
  type        = string
  default     = "local-ai-platform-qdrant-data"
}

variable "rag_collection_name" {
  description = "Qdrant collection name used by the platform API."
  type        = string
  default     = "platform_documents"

  validation {
    condition     = can(regex("^[A-Za-z0-9_-]+$", var.rag_collection_name))
    error_message = "rag_collection_name may contain only letters, numbers, underscores, and hyphens."
  }
}

variable "rag_ingestion_timeout_seconds" {
  description = "End-to-end deadline for synchronous PDF upload and indexing."
  type        = number
  default     = 120

  validation {
    condition     = var.rag_ingestion_timeout_seconds > 0 && var.rag_ingestion_timeout_seconds <= 3600
    error_message = "rag_ingestion_timeout_seconds must be greater than 0 and no more than 3600."
  }
}

variable "rag_max_indexed_chunks" {
  description = "Provisional maximum of 25000 indexed chunks; tune after measuring target-host Qdrant growth."
  type        = number
  default     = 25000
  nullable    = true

  validation {
    condition     = var.rag_max_indexed_chunks == null || (var.rag_max_indexed_chunks >= 1 && floor(var.rag_max_indexed_chunks) == var.rag_max_indexed_chunks)
    error_message = "rag_max_indexed_chunks must be a positive whole number when set."
  }
}

variable "rag_max_pdf_pages" {
  description = "Optional practical PDF page limit, to be set after target-host validation."
  type        = number
  default     = null
  nullable    = true

  validation {
    condition     = var.rag_max_pdf_pages == null || (var.rag_max_pdf_pages >= 1 && floor(var.rag_max_pdf_pages) == var.rag_max_pdf_pages)
    error_message = "rag_max_pdf_pages must be a positive whole number when set."
  }
}

variable "rag_score_threshold" {
  description = "Optional override for the app's provisional 0.5 threshold; set the calibrated cutoff when available."
  type        = number
  default     = null
  nullable    = true

  validation {
    condition     = var.rag_score_threshold == null || (var.rag_score_threshold >= 0 && var.rag_score_threshold <= 1)
    error_message = "rag_score_threshold must be between 0 and 1 when set."
  }
}

variable "request_timeout_seconds" {
  description = "Maximum time the API waits for an Ollama response."
  type        = number
  default     = 120

  validation {
    condition     = var.request_timeout_seconds > 0 && var.request_timeout_seconds <= 3600
    error_message = "request_timeout_seconds must be greater than 0 and no more than 3600."
  }
}
