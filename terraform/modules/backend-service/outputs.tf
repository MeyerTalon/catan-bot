output "alb_dns_name" {
  description = "ALB hostname; use as the CloudFront API origin."
  value       = aws_lb.this.dns_name
}

output "security_group_id" {
  description = "Security group attached to the task; allow it on downstream resources (RDS)."
  value       = aws_security_group.tasks.id
}

output "ecr_repository_url" {
  description = "ECR repository URL to push images to."
  value       = aws_ecr_repository.this.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN."
  value       = aws_ecr_repository.this.arn
}

output "cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ECS service ARN."
  value       = aws_ecs_service.this.id
}

output "task_role_name" {
  description = "Task role name; attach application permissions (e.g. Cognito) here."
  value       = aws_iam_role.task.name
}

output "log_group_name" {
  description = "CloudWatch log group for container output."
  value       = aws_cloudwatch_log_group.this.name
}
