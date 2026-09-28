provider "aws" {
  region = local.aws_region

  default_tags {
    tags = {
      Project     = local.project
      Environment = local.environment
      ManagedBy   = "terraform"
    }
  }
}

# cloudfront only reads acm certificates from us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = local.project
      Environment = local.environment
      ManagedBy   = "terraform"
    }
  }
}

# dns for the custom domain (registered with cloudflare, which requires its own
# name servers). reads CLOUDFLARE_API_TOKEN from the environment; only needed
# once local.domain is set
provider "cloudflare" {}
