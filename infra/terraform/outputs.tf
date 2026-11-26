output "api_url" {
  description = "Loopback URL for the platform API."
  value       = "http://127.0.0.1:${var.api_host_port}"
}

output "open_webui_url" {
  description = "Loopback URL for the Open WebUI chat interface."
  value       = "http://127.0.0.1:${var.open_webui_host_port}"
}

output "ollama_internal_url" {
  description = "Ollama URL available only to containers on the platform network."
  value       = "http://ollama:11434"
}

output "docling_internal_url" {
  description = "Docling Serve URL available only to containers on the RAG network."
  value       = "http://docling:5001"
}

output "qdrant_internal_url" {
  description = "Qdrant URL available only to containers on the RAG network."
  value       = "http://qdrant:6333"
}

output "qdrant_volume_name" {
  description = "Persistent Docker volume containing the Qdrant index."
  value       = var.qdrant_volume_name
}

output "ollama_volume_name" {
  description = "Persistent Docker volume containing Ollama model artifacts."
  value       = var.ollama_volume_name
}

output "open_webui_volume_name" {
  description = "Persistent Docker volume containing Open WebUI conversations and settings."
  value       = var.open_webui_volume_name
}
