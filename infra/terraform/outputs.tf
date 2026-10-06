output "api_url" {
  description = "Loopback URL for the platform API."
  value       = "http://127.0.0.1:${var.api_host_port}"
}

output "ollama_internal_url" {
  description = "Ollama URL available only to containers on the platform network."
  value       = "http://ollama:11434"
}

output "ollama_volume_name" {
  description = "Persistent Docker volume containing Ollama model artifacts."
  value       = var.ollama_volume_name
}
