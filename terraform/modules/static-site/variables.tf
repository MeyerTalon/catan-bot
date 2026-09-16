variable "name" {
  description = "Name prefix for site resources (e.g. catan-prod-frontend)."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for the built assets."
  type        = string
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete a non-empty bucket."
  type        = bool
  default     = false
}

variable "domain_names" {
  description = "Custom domain aliases for the distribution. Requires certificate_arn."
  type        = list(string)
  default     = []
}

variable "certificate_arn" {
  description = "ACM certificate ARN in us-east-1 covering domain_names. Empty uses the default *.cloudfront.net cert."
  type        = string
  default     = ""

  validation {
    condition     = var.certificate_arn == "" || can(regex("^arn:aws:acm:us-east-1:", var.certificate_arn))
    error_message = "CloudFront certificates must be issued in us-east-1."
  }
}

variable "spa_fallback" {
  description = "Serve index.html with 200 for 403/404 so client-side routing works."
  type        = bool
  default     = true
}

variable "price_class" {
  description = "CloudFront price class. PriceClass_100 = North America + Europe only."
  type        = string
  default     = "PriceClass_100"
}
