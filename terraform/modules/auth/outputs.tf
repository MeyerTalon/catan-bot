output "user_pool_id" {
  description = "Cognito user pool ID (COGNITO_USER_POOL_ID)."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "Cognito user pool ARN."
  value       = aws_cognito_user_pool.this.arn
}

output "client_id" {
  description = "App client ID (COGNITO_CLIENT_ID)."
  value       = aws_cognito_user_pool_client.this.id
}

output "client_secret" {
  description = "App client secret; empty unless generate_client_secret = true."
  value       = aws_cognito_user_pool_client.this.client_secret
  sensitive   = true
}
