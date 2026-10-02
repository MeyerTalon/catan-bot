# Production environment: composes the shared modules. Every sizing decision
# lives in this locals block so the diff between environments is obvious.
#
# Idle cost with these values is about $56/month (ALB + 4 public IPv4s ≈ $31,
# db.t4g.micro ≈ $14, one Fargate Spot task ≈ $3, t3.micro bastion ≈ $8,
# everything else ≈ $0). See ../../ARCHITECTURE.md for the per-resource
# breakdown.

locals {
  project     = "catan"
  environment = "prod"
  aws_region  = "us-west-2"
  name        = "${local.project}-${local.environment}"

  # set to "" to skip the GitHub Actions deploy role
  github_repository = "MeyerTalon/catan-bot"

  # custom domain registered with cloudflare; "" serves only *.cloudfront.net.
  # the zone id is on the cloudflare dashboard (domain → overview), not a secret
  domain             = "catanbot.ai"
  cloudflare_zone_id = "4b11b7666665ed015a1c0cf4553a9f3b"
  site_hostnames     = local.domain != "" ? [local.domain, "www.${local.domain}"] : []
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# network
# ---------------------------------------------------------------------------

module "network" {
  source = "../../modules/network"

  name     = local.name
  vpc_cidr = "10.0.0.0/16"
}

# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------

module "database" {
  source = "../../modules/database"

  name       = local.name
  vpc_id     = module.network.vpc_id
  subnet_ids = module.network.public_subnet_ids
  allowed_security_group_ids = {
    backend = module.backend.security_group_id
    bastion = module.bastion.security_group_id
  }

  instance_class     = "db.t4g.micro"
  allocated_storage  = 20
  ssl_root_cert_path = "/app/rds-global-bundle.pem" # shipped by backend/Dockerfile
  # free-plan accounts reject >1 day (FreeTierRestrictionError)
  backup_retention_days = 1
  # protected unless terraform-destroy.yml flips allow_destroy; no final
  # snapshot then, so repeated destroy/rebuild cycles never collide on its name
  deletion_protection = !var.allow_destroy
  skip_final_snapshot = var.allow_destroy
}

# ---------------------------------------------------------------------------
# bastion (ssm port forward to rds for datagrip / psql; `mise run db:tunnel`)
# ---------------------------------------------------------------------------

module "bastion" {
  source = "../../modules/bastion"

  name      = local.name
  vpc_id    = module.network.vpc_id
  vpc_cidr  = module.network.vpc_cidr
  subnet_id = module.network.public_subnet_ids[0]

  # this account is on the aws free plan, which refuses every instance type
  # outside a short allowlist — including the cheaper graviton t4g.nano and
  # t4g.micro that describe-instance-types reports as eligible
  # (InvalidParameterCombination on RunInstances). t3.micro is what it launches
  instance_type = "t3.micro"
}

# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

module "auth" {
  source = "../../modules/auth"

  name                   = local.name
  generate_client_secret = false
  deletion_protection    = !var.allow_destroy
}

# ---------------------------------------------------------------------------
# backend api
# ---------------------------------------------------------------------------

module "backend" {
  source = "../../modules/backend-service"

  name       = "${local.name}-backend"
  vpc_id     = module.network.vpc_id
  subnet_ids = module.network.public_subnet_ids

  image_tag         = var.backend_image_tag
  container_port    = 8000
  health_check_path = "/health"

  cpu              = 256
  memory           = 512
  desired_count    = 1
  use_fargate_spot = true

  # only our cloudfront distribution may talk to the alb (ip prefix list plus
  # the x-origin-verify secret); the api is reached at ${frontend_url}/api
  restrict_ingress_to_cloudfront = true
  require_origin_verify_header   = true

  # pool/client ids are not secrets; only the db url is
  environment = {
    ENVIRONMENT          = "production"
    PORT                 = "8000"
    COGNITO_REGION       = local.aws_region
    COGNITO_USER_POOL_ID = module.auth.user_pool_id
    COGNITO_CLIENT_ID    = module.auth.client_id
    TRUSTED_PROXY_HOPS   = "2" # cloudfront, then the alb, append to x-forwarded-for
  }

  secrets = [
    { name = "DATABASE_URL", value_from = module.database.database_url_parameter_arn },
  ]
  parameter_arns = [module.database.database_url_parameter_arn]
}

# ---------------------------------------------------------------------------
# frontend + api edge
# ---------------------------------------------------------------------------

module "frontend" {
  source = "../../modules/static-site"

  name          = "${local.name}-frontend"
  bucket_name   = "${local.name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.allow_destroy # empties the bucket on destroy

  enable_api_origin         = true
  api_origin_domain_name    = module.backend.alb_dns_name
  api_path_prefix           = "/api"
  api_origin_custom_headers = module.backend.origin_verify_header

  aliases             = local.site_hostnames
  acm_certificate_arn = local.domain != "" ? aws_acm_certificate_validation.site[0].certificate_arn : null
}

# ---------------------------------------------------------------------------
# custom domain (acm certificate + cloudflare dns)
# ---------------------------------------------------------------------------

resource "aws_acm_certificate" "site" {
  count    = local.domain != "" ? 1 : 0
  provider = aws.us_east_1

  domain_name               = local.domain
  subject_alternative_names = [for h in local.site_hostnames : h if h != local.domain]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# records must stay dns-only (grey cloud): proxying would put cloudflare's cdn
# in front of cloudfront and hide the validation cname from acm
resource "cloudflare_dns_record" "cert_validation" {
  for_each = local.domain != "" ? {
    for o in aws_acm_certificate.site[0].domain_validation_options : o.domain_name => o
  } : {}

  zone_id = local.cloudflare_zone_id
  name    = trimsuffix(each.value.resource_record_name, ".")
  type    = each.value.resource_record_type
  content = trimsuffix(each.value.resource_record_value, ".")
  ttl     = 1 # automatic
  proxied = false
}

resource "aws_acm_certificate_validation" "site" {
  count    = local.domain != "" ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for o in aws_acm_certificate.site[0].domain_validation_options : o.resource_record_name]

  depends_on = [cloudflare_dns_record.cert_validation]
}

# cloudflare flattens the apex cname into a/aaaa answers
resource "cloudflare_dns_record" "site" {
  for_each = toset(local.site_hostnames)

  zone_id = local.cloudflare_zone_id
  name    = each.value
  type    = "CNAME"
  content = module.frontend.distribution_domain_name
  ttl     = 1 # automatic
  proxied = false
}

# ---------------------------------------------------------------------------
# github actions deploy role (app deploys only; the terraform role is in bootstrap)
# ---------------------------------------------------------------------------

data "aws_iam_openid_connect_provider" "github" {
  count = local.github_repository != "" ? 1 : 0

  url = "https://token.actions.githubusercontent.com"
}

module "deploy_role" {
  count  = local.github_repository != "" ? 1 : 0
  source = "../../modules/deploy-role"

  name                = "${local.name}-github-deploy"
  oidc_provider_arn   = data.aws_iam_openid_connect_provider.github[0].arn
  github_repository   = local.github_repository
  github_environments = ["production"]

  ecr_repository_arns          = [module.backend.ecr_repository_arn]
  ecs_service_arns             = [module.backend.service_arn]
  passable_role_arns           = [module.backend.execution_role_arn, module.backend.task_role_arn]
  s3_bucket_arns               = [module.frontend.bucket_arn]
  cloudfront_distribution_arns = [module.frontend.distribution_arn]
}
