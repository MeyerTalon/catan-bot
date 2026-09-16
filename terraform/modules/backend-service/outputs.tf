output "url" {
  description = "Public base URL of the service (ALB DNS name, http or https)."
  value       = local.url
}

output "alb_dns_name" {
  description = "ALB DNS name (point a CNAME here for a custom domain)."
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID for Route 53 alias records."
  value       = aws_lb.this.zone_id
}

output "security_group_id" {
  description = "Security group attached to the ECS tasks; allow it on downstream resources."
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

output "cluster_arn" {
  description = "ECS cluster ARN."
  value       = aws_ecs_cluster.this.arn
}

output "service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ECS service ARN."
  value       = aws_ecs_service.this.id
}

output "task_execution_role_arn" {
  description = "Task execution role ARN."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "Task role ARN; attach app permissions here."
  value       = aws_iam_role.task.arn
}

output "task_role_name" {
  description = "Task role name, for aws_iam_role_policy attachments."
  value       = aws_iam_role.task.name
}

output "log_group_name" {
  description = "CloudWatch log group for container output."
  value       = aws_cloudwatch_log_group.this.name
}

output "task_definition_family_arn" {
  description = "Wildcard ARN for every revision of the task definition (for ecs:RunTask grants)."
  value       = "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/${aws_ecs_task_definition.this.family}:*"
}

output "task_subnet_ids" {
  description = "Subnets tasks run in (for one-off aws ecs run-task invocations)."
  value       = var.task_subnet_ids
}
