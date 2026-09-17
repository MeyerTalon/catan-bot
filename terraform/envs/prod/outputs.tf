output "frontend_url" {
  description = "Public site URL."
  value       = module.frontend.url
}

output "backend_url" {
  description = "Public API base URL (through CloudFront). Bake into the frontend as VITE_BACKEND_URL."
  value       = module.frontend.api_url
}

output "alb_dns_name" {
  description = "Raw ALB hostname; only reachable from CloudFront unless restrict_ingress_to_cloudfront is off."
  value       = module.backend.alb_dns_name
}

output "ecr_repository_url" {
  description = "Push backend images here."
  value       = module.backend.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster (for aws ecs update-service)."
  value       = module.backend.cluster_name
}

output "ecs_service_name" {
  description = "ECS service (for aws ecs update-service)."
  value       = module.backend.service_name
}

output "log_group_name" {
  description = "Backend container logs."
  value       = module.backend.log_group_name
}

output "frontend_bucket" {
  description = "Sync frontend/dist here."
  value       = module.frontend.bucket_name
}

output "cloudfront_distribution_id" {
  description = "Invalidate after every frontend deploy."
  value       = module.frontend.distribution_id
}

output "database_url" {
  description = "Postgres URL (sensitive). Same value the task receives as DATABASE_URL."
  value       = module.database.connection_url
  sensitive   = true
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID (COGNITO_USER_POOL_ID)."
  value       = module.auth.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito app client ID (COGNITO_CLIENT_ID)."
  value       = module.auth.client_id
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_ROLE_ARN repository secret in GitHub."
  value       = local.github_repository != "" ? module.deploy_role[0].role_arn : ""
}
