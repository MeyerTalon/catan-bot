output "url" {
  description = "Public URL of the site."
  value       = local.url
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
  description = "*.cloudfront.net hostname (CNAME target for custom domains)."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "distribution_hosted_zone_id" {
  description = "CloudFront hosted zone ID for Route 53 alias records."
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}
