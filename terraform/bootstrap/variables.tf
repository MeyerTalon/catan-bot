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
  description = "GitHub repository (owner/name) whose Actions may run Terraform. Empty skips the OIDC provider and CI roles."
  type        = string
  default     = ""
}

variable "terraform_apply_branch" {
  description = "Branch allowed to assume the apply role."
  type        = string
  default     = "main"
}
