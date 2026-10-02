# everything else is a local in main.tf; these are the only knobs CI overrides.
# per deploy (terraform apply -var backend_image_tag=sha-abc123)
variable "backend_image_tag" {
  description = "ECR image tag the backend service runs."
  type        = string
  default     = "latest"
}

# only terraform-destroy.yml sets this: it applies allow_destroy=true to the
# protected resources, then destroys the stack in the same job
variable "allow_destroy" {
  description = "Lift deletion protection on RDS (and skip its final snapshot), the Cognito pool, and the frontend bucket (force_destroy) so terraform destroy removes everything. Data loss on destroy; keep false outside the destroy workflow."
  type        = bool
  default     = false
}
