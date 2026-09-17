# Production environment: composes the shared modules. Every sizing decision
# lives in this locals block so the diff between environments is obvious.
#
# Idle cost with these values is about $44/month (ALB + 3 public IPv4s ≈ $27,
# db.t4g.micro ≈ $14, one Fargate Spot task ≈ $3, everything else ≈ $0). See
# ../../ARCHITECTURE.md for the per-resource breakdown.

locals {
  project     = "catan"
  environment = "prod"
  aws_region  = "us-west-2"
  name        = "${local.project}-${local.environment}"

  # set to "" to skip the GitHub Actions deploy role
  github_repository = "MeyerTalon/catan-bot"
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

  name                       = local.name
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.public_subnet_ids
  allowed_security_group_ids = { backend = module.backend.security_group_id }

  instance_class    = "db.t4g.micro"
  allocated_storage = 20
  # free-plan accounts reject >1 day (FreeTierRestrictionError)
  backup_retention_days = 1
  deletion_protection   = true
  skip_final_snapshot   = false
}

# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

module "auth" {
  source = "../../modules/auth"

  name                   = local.name
  generate_client_secret = false
  deletion_protection    = true
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

  # only cloudfront may talk to the alb; the api is reached at ${frontend_url}/api
  restrict_ingress_to_cloudfront = true

  # pool/client ids are not secrets; only the db url is
  environment = {
    ENVIRONMENT          = "production"
    PORT                 = "8000"
    COGNITO_REGION       = local.aws_region
    COGNITO_USER_POOL_ID = module.auth.user_pool_id
    COGNITO_CLIENT_ID    = module.auth.client_id
  }

  secrets = [
    { name = "DATABASE_URL", value_from = module.database.database_url_parameter_arn },
  ]
  parameter_arns = [module.database.database_url_parameter_arn]
}

# the backend confirms sign-ups itself, which is an admin call on the pool
resource "aws_iam_role_policy" "backend_cognito" {
  name   = "cognito"
  role   = module.backend.task_role_name
  policy = module.auth.backend_policy_json
}

# ---------------------------------------------------------------------------
# frontend + api edge
# ---------------------------------------------------------------------------

module "frontend" {
  source = "../../modules/static-site"

  name          = "${local.name}-frontend"
  bucket_name   = "${local.name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = false

  enable_api_origin      = true
  api_origin_domain_name = module.backend.alb_dns_name
  api_path_prefix        = "/api"
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
  s3_bucket_arns               = [module.frontend.bucket_arn]
  cloudfront_distribution_arns = [module.frontend.distribution_arn]
}
