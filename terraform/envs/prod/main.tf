# Production environment. Composes the shared modules; environment-specific
# sizing lives in the locals block so the diff between envs is obvious.
#
# Idle cost with these defaults is roughly $30-45/month (ALB + db.t4g.micro +
# one Fargate Spot task). Enabling NAT or multi-AZ roughly doubles it.

locals {
  project     = "catan"
  environment = "prod"
  aws_region  = "us-west-2"
  name        = "${local.project}-${local.environment}"

  # set to "" to skip the GitHub Actions deploy role
  github_repository = "MeyerTalon/catan-bot"

  # optional TLS. the ALB cert must be in local.aws_region; the CloudFront cert
  # must be in us-east-1. leave empty for http / *.cloudfront.net only.
  backend_certificate_arn  = ""
  frontend_certificate_arn = ""
  frontend_domain_names    = []
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# network
# ---------------------------------------------------------------------------

module "network" {
  source = "../../modules/network"

  name               = local.name
  vpc_cidr           = "10.0.0.0/16"
  az_count           = 2
  enable_nat_gateway = false
}

# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------

module "database" {
  source = "../../modules/database"

  name                       = local.name
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.private_subnet_ids
  allowed_security_group_ids = [module.backend.security_group_id]

  instance_class        = "db.t4g.micro"
  allocated_storage     = 20
  max_allocated_storage = 100
  multi_az              = false
  backup_retention_days = 7
  deletion_protection   = true
  skip_final_snapshot   = false
}

# ---------------------------------------------------------------------------
# auth (cognito)
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

  name             = "${local.name}-backend"
  vpc_id           = module.network.vpc_id
  alb_subnet_ids   = module.network.public_subnet_ids
  task_subnet_ids  = module.network.public_subnet_ids
  assign_public_ip = true

  image_tag         = var.backend_image_tag
  container_port    = 8000
  health_check_path = "/health"

  cpu                = 256
  memory             = 512
  min_count          = 1
  max_count          = 2
  cpu_target_percent = 70
  use_fargate_spot   = true

  certificate_arn = local.backend_certificate_arn

  # pool/client ids are not secrets; only the db url is
  environment = {
    ENVIRONMENT          = "production"
    PORT                 = "8000"
    COGNITO_REGION       = local.aws_region
    COGNITO_USER_POOL_ID = module.auth.user_pool_id
    COGNITO_CLIENT_ID    = module.auth.client_id
  }

  secrets = [
    { name = "DATABASE_URL", value_from = "${module.database.secret_arn}:DATABASE_URL::" },
  ]
  secret_arns = [module.database.secret_arn]
}

# the backend confirms sign-ups itself, which is an admin call on the pool
resource "aws_iam_role_policy" "backend_cognito" {
  name   = "cognito"
  role   = module.backend.task_role_name
  policy = module.auth.backend_policy_json
}

# ---------------------------------------------------------------------------
# frontend
# ---------------------------------------------------------------------------

module "frontend" {
  source = "../../modules/static-site"

  name            = "${local.name}-frontend"
  bucket_name     = "${local.name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy   = false
  domain_names    = local.frontend_domain_names
  certificate_arn = local.frontend_certificate_arn
}

# ---------------------------------------------------------------------------
# github actions deploy role (app deploys only; terraform CI roles are in bootstrap)
# ---------------------------------------------------------------------------

data "aws_iam_openid_connect_provider" "github" {
  count = local.github_repository != "" ? 1 : 0

  url = "https://token.actions.githubusercontent.com"
}

module "deploy_role" {
  count  = local.github_repository != "" ? 1 : 0
  source = "../../modules/deploy-role"

  name              = "${local.name}-github-deploy"
  oidc_provider_arn = data.aws_iam_openid_connect_provider.github[0].arn
  github_repository = local.github_repository
  github_refs       = ["refs/heads/main"]

  ecr_repository_arns          = [module.backend.ecr_repository_arn]
  ecs_service_arns             = [module.backend.service_arn]
  ecs_task_definition_arns     = [module.backend.task_definition_family_arn]
  ecs_task_role_arns           = [module.backend.task_execution_role_arn, module.backend.task_role_arn]
  s3_bucket_arns               = [module.frontend.bucket_arn]
  cloudfront_distribution_arns = [module.frontend.distribution_arn]
}
