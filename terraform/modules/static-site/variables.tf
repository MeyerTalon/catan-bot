variable "name" {
  description = "Name prefix for site resources (e.g. catan-prod-frontend)."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for the built assets."
  type        = string
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete a non-empty bucket."
  type        = bool
  default     = false
}

variable "api_origin_domain_name" {
  description = "Hostname (e.g. the ALB DNS name) that requests under api_path_prefix are proxied to over plain HTTP. Empty disables the API behavior."
  type        = string
  default     = ""
}

variable "api_path_prefix" {
  description = "Path prefix that is routed to the API origin. The prefix is stripped before forwarding, so /api/health reaches the origin as /health."
  type        = string
  default     = "/api"

  validation {
    condition     = can(regex("^/[a-z0-9-]+$", var.api_path_prefix))
    error_message = "api_path_prefix must look like /api (leading slash, no trailing slash)."
  }
}
