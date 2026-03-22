variable "project" {
  description = "Project name used in all resource naming"
  type        = string
  default     = "linkpulse"
}

variable "environment" {
  description = "Environment name: main"
  type        = string
  default     = "main"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

variable "container_image" {
  description = "Full container image URI (e.g. linkpulseacrmain.azurecr.io/linkpulse:abc123)"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

