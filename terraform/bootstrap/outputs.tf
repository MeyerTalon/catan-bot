output "state_bucket" {
  description = "Remote state bucket. Put this in each env's backend.hcl."
  value       = aws_s3_bucket.state.id
}

output "aws_region" {
  description = "Region the state bucket lives in."
  value       = var.aws_region
}

output "github_oidc_provider_arn" {
  description = "GitHub Actions OIDC provider ARN (empty if github_repository is unset)."
  value       = local.github_enabled ? aws_iam_openid_connect_provider.github[0].arn : ""
}

output "terraform_plan_role_arn" {
  description = "Set as the AWS_TERRAFORM_PLAN_ROLE_ARN repository variable in GitHub."
  value       = local.github_enabled ? aws_iam_role.terraform_plan[0].arn : ""
}

output "terraform_apply_role_arn" {
  description = "Set as the AWS_TERRAFORM_APPLY_ROLE_ARN repository variable in GitHub."
  value       = local.github_enabled ? aws_iam_role.terraform_apply[0].arn : ""
}
