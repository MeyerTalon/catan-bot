output "address" {
  description = "RDS hostname (private)."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "Postgres port."
  value       = aws_db_instance.this.port
}

output "db_name" {
  description = "Database name."
  value       = aws_db_instance.this.db_name
}

output "security_group_id" {
  description = "Security group attached to the instance."
  value       = aws_security_group.this.id
}

output "secret_arn" {
  description = "Secrets Manager secret ARN holding DATABASE_URL and the credential parts."
  value       = aws_secretsmanager_secret.this.arn
}

output "connection_url" {
  description = "Full Postgres URL (sensitive). Use for running migrations."
  value       = local.connection_url
  sensitive   = true
}
