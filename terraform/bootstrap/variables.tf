variable "project_name" {
  description = "Short project slug used in resource names."
  type        = string
  default     = "catan"
}

variable "aws_region" {
  description = "Region for the state bucket and IAM resources."
  type        = string
  default     = "us-west-2"
}

variable "github_repository" {
  description = "GitHub repository (owner/name) whose Actions may run terraform apply. Empty skips the OIDC provider and role."
  type        = string
  default     = ""
}

variable "github_environments" {
  description = "GitHub environments whose jobs may assume the terraform-apply role. terraform.yml plans in production-plan and applies in production; restrict both to main and put reviewers on production in GitHub."
  type        = list(string)
  default     = ["production", "production-plan"]
}

variable "budget_alert_email" {
  description = "Email for the monthly cost alert. Empty skips the budget."
  type        = string
  default     = ""
}

variable "budget_limit_usd" {
  description = "Monthly spend that triggers the alert (actual and forecasted)."
  type        = number
  default     = 10
}
