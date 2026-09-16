output "role_arn" {
  description = "Role ARN to configure in GitHub Actions (aws-actions/configure-aws-credentials role-to-assume)."
  value       = aws_iam_role.this.arn
}
