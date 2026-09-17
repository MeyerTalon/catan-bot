output "address" {
  description = "RDS hostname (private)."
  value       = aws_db_instance.this.address
}

output "security_group_id" {
  description = "Security group attached to the instance."
  value       = aws_security_group.this.id
}

output "database_url_parameter_arn" {
  description = "SSM SecureString parameter ARN holding DATABASE_URL (use as an ECS secret valueFrom)."
  value       = aws_ssm_parameter.database_url.arn
}

output "connection_url" {
  description = "Full Postgres URL (sensitive)."
  value       = local.connection_url
  sensitive   = true
}
