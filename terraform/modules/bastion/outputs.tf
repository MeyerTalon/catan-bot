output "instance_id" {
  description = "EC2 instance ID (the --target of aws ssm start-session)."
  value       = aws_instance.this.id
}

output "security_group_id" {
  description = "Security group attached to the instance; allow it into whatever the port forward should reach."
  value       = aws_security_group.this.id
}
