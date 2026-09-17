output "url" {
  description = "Public URL of the site (and, under api_path_prefix, the API)."
  value       = "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "api_url" {
  description = "Public base URL of the API through CloudFront; empty if no API origin was given."
  value       = local.api_enabled ? "https://${aws_cloudfront_distribution.this.domain_name}${var.api_path_prefix}" : ""
}

output "bucket_name" {
  description = "S3 bucket to sync the build output into."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "S3 bucket ARN."
  value       = aws_s3_bucket.this.arn
}

output "distribution_id" {
  description = "CloudFront distribution ID (for invalidations)."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_arn" {
  description = "CloudFront distribution ARN."
  value       = aws_cloudfront_distribution.this.arn
}
