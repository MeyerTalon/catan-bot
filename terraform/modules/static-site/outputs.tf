output "url" {
  description = "Public URL of the site (and, under api_path_prefix, the API)."
  value       = "https://${local.site_host}"
}

output "api_url" {
  description = "Public base URL of the API through CloudFront; empty unless enable_api_origin is true."
  value       = local.api_enabled ? "https://${local.site_host}${var.api_path_prefix}" : ""
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

output "distribution_domain_name" {
  description = "The distribution's *.cloudfront.net hostname; point custom-domain DNS records (CNAME / ALIAS) at it."
  value       = aws_cloudfront_distribution.this.domain_name
}
