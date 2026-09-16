# everything else is a local in main.tf; this is the one knob CI may override
# per deploy (terraform apply -var backend_image_tag=sha-abc123).
variable "backend_image_tag" {
  description = "ECR image tag the backend service runs."
  type        = string
  default     = "latest"
}
