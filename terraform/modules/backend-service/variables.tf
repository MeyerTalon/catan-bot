variable "name" {
  description = "Name prefix for service resources (e.g. catan-prod-backend)."
  type        = string
}

variable "vpc_id" {
  description = "VPC for the ALB, task, and security groups."
  type        = string
}

variable "subnet_ids" {
  description = "Public subnet IDs for the ALB and the task (at least two AZs for the ALB)."
  type        = list(string)
}

variable "image_tag" {
  description = "Tag of the image the task definition template references. Only the first deployment runs it: later deploys register their own revision with :<git sha> (tags are immutable), and the service ignores task definition drift."
  type        = string
  default     = "latest"
}

variable "container_port" {
  description = "Port the container listens on."
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "HTTP path the ALB polls; must return 200."
  type        = string
  default     = "/health"
}

variable "cpu" {
  description = "Fargate CPU units per task (256 = 0.25 vCPU, the minimum)."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate memory per task in MiB (512 is the minimum for 256 CPU)."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of tasks. Each one costs Fargate time plus a public IPv4 (~$3.65/month)."
  type        = number
  default     = 1
}

variable "use_fargate_spot" {
  description = "Run on FARGATE_SPOT (~70% cheaper, may be interrupted and restarted)."
  type        = bool
  default     = true
}

variable "environment" {
  description = "Plain environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Values injected as env vars at start. value_from is an SSM parameter ARN."
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []
}

variable "parameter_arns" {
  description = "SSM parameter ARNs the task execution role may read (every ARN used in var.secrets)."
  type        = list(string)
  default     = []
}

variable "require_origin_verify_header" {
  description = "Forward only requests that carry the generated X-Origin-Verify secret (exposed as origin_verify_header) and answer everything else 403. Set false to hit the ALB directly."
  type        = bool
  default     = true
}

variable "restrict_ingress_to_cloudfront" {
  description = "Only accept ALB traffic from CloudFront's origin-facing IP ranges. Set false to hit the ALB directly."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention for container logs."
  type        = number
  default     = 14
}
