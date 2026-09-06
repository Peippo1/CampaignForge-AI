variable "project_id" {
  description = "GCP project hosting CampaignForge."
  type        = string
}

variable "region" {
  description = "Single-region default for data and compute."
  type        = string
  default     = "europe-west2"
}

variable "environment" {
  type    = string
  default = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "api_image" {
  description = "Immutable Artifact Registry image reference."
  type        = string
}

variable "database_tier" {
  description = "Use db-f1-micro for low-traffic staging; increase before production load."
  type        = string
  default     = "db-f1-micro"
}
