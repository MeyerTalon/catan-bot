variable "name" {
  description = "Name prefix for service resources (e.g. catan-prod-backend)."
  type        = string
}

variable "vpc_id" {
  description = "VPC for the ALB, tasks, and security groups."
  type        = string
}

variable "alb_subnet_ids" {
  description = "Public subnet IDs for the ALB (at least two AZs)."
  type        = list(string)
}

variable "task_subnet_ids" {
  description = "Subnet IDs for ECS tasks. Public subnets with assign_public_ip = true, or private subnets behind a NAT gateway."
  type        = list(string)
}

variable "assign_public_ip" {
  description = "Give tasks a public IP so they can reach ECR/Secrets Manager/Supabase without a NAT gateway."
  type        = bool
  default     = true
}

variable "image_tag" {
  description = "Tag of the image in this module's ECR repository to run."
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
  description = "Fargate CPU units per task (256 = 0.25 vCPU)."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate memory per task in MiB."
  type        = number
  default     = 512
}

variable "min_count" {
  description = "Minimum running tasks (also the initial desired count)."
  type        = number
  default     = 1
}

variable "max_count" {
  description = "Maximum tasks autoscaling may run. Set equal to min_count to pin."
  type        = number
  default     = 2
}

variable "cpu_target_percent" {
  description = "Average CPU utilisation autoscaling aims for."
  type        = number
  default     = 70
}

variable "use_fargate_spot" {
  description = "Run on FARGATE_SPOT (cheaper, may be interrupted) instead of FARGATE."
  type        = bool
  default     = true
}

variable "environment" {
  description = "Plain environment variables for the container."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets injected as env vars. value_from is a Secrets Manager ARN, optionally with ':json-key::' suffix."
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []
}

variable "secret_arns" {
  description = "Secrets Manager ARNs the task execution role may read (every ARN referenced in var.secrets)."
  type        = list(string)
  default     = []
}

variable "certificate_arn" {
  description = "ACM certificate ARN (same region) for HTTPS on the ALB. Empty serves plain HTTP."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention for container logs."
  type        = number
  default     = 14
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights on the cluster (extra cost)."
  type        = bool
  default     = false
}

variable "enable_execute_command" {
  description = "Allow `aws ecs execute-command` shells into running tasks."
  type        = bool
  default     = false
}

variable "ecr_image_retention_count" {
  description = "How many images to keep in ECR before the lifecycle policy expires old ones."
  type        = number
  default     = 20
}
