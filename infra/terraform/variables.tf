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
  default     = "local-ai-platform-api:1.0.0"
}

variable "default_model" {
  description = "Default Ollama model requested by the platform API."
  type        = string
  default     = "qwen2.5:1.5b"

  validation {
    condition     = length(trimspace(var.default_model)) > 0
    error_message = "default_model must not be empty."
  }
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
  default     = "ollama/ollama:0.35.1"
}

variable "ollama_volume_name" {
  description = "Docker volume that retains Ollama model artifacts across Terraform destroy."
  type        = string
  default     = "local-ai-platform-ollama-models"
}

variable "platform_network_name" {
  description = "Docker bridge network shared by the API and Ollama containers."
  type        = string
  default     = "local-ai-platform"
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
