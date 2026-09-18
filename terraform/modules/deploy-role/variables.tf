variable "name" {
  description = "IAM role name (e.g. catan-prod-github-deploy)."
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the account's GitHub Actions OIDC provider (created by terraform/bootstrap)."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the role, as owner/name."
  type        = string
}

variable "github_environments" {
  description = "GitHub environment names whose jobs may assume the role (the OIDC sub claim is repo:<owner/name>:environment:<name>). Restrict branches and require reviewers on the environment itself in GitHub."
  type        = list(string)
  default     = ["production"]
}

variable "ecr_repository_arns" {
  description = "ECR repositories the role may push to."
  type        = list(string)
  default     = []
}

variable "ecs_service_arns" {
  description = "ECS services the role may redeploy (UpdateService --force-new-deployment)."
  type        = list(string)
  default     = []
}

variable "s3_bucket_arns" {
  description = "S3 buckets the role may sync frontend builds into."
  type        = list(string)
  default     = []
}

variable "cloudfront_distribution_arns" {
  description = "CloudFront distributions the role may invalidate."
  type        = list(string)
  default     = []
}

variable "passable_role_arns" {
  description = "ECS execution/task role ARNs the deploy role may pass when registering a task definition."
  type        = list(string)
  default     = []
}
