# One-time, per-account foundation for every other stack:
#   * the S3 bucket that stores remote state (native lockfile locking, no DynamoDB)
#   * the GitHub Actions OIDC provider (one per AWS account)
#   * two CI roles for Terraform itself: read-only plan on pull requests,
#     admin apply on the main branch
#
# Apply once with local state, then never touch it unless the account changes.

data "aws_caller_identity" "current" {}

locals {
  github_enabled    = var.github_repository != ""
  state_bucket_name = "${var.project_name}-terraform-state-${data.aws_caller_identity.current.account_id}"
}

# ---------------------------------------------------------------------------
# remote state bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "state" {
  bucket = local.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ---------------------------------------------------------------------------
# github oidc
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  count = local.github_enabled ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # aws has validated github's cert chain against its own trust store since
  # mid-2023, so these thumbprints are no longer used for trust; the api still
  # requires the field.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "github_plan_assume" {
  count = local.github_enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repository}:pull_request",
        "repo:${var.github_repository}:ref:refs/heads/${var.terraform_apply_branch}",
      ]
    }
  }
}

data "aws_iam_policy_document" "github_apply_assume" {
  count = local.github_enabled ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/${var.terraform_apply_branch}"]
    }
  }
}

# state access shared by both roles. plan runs with -lock=false so it only
# needs to read; apply needs to write state and the lockfile.
data "aws_iam_policy_document" "state_read" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.state.arn]
  }

  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.state.arn}/*"]
  }

  # ReadOnlyAccess can describe secrets but not read them; refreshing
  # aws_secretsmanager_secret_version resources needs the value.
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-*"]
  }
}

data "aws_iam_policy_document" "state_write" {
  statement {
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/*"]
  }
}

resource "aws_iam_role" "terraform_plan" {
  count = local.github_enabled ? 1 : 0

  name               = "${var.project_name}-terraform-plan"
  assume_role_policy = data.aws_iam_policy_document.github_plan_assume[0].json
}

resource "aws_iam_role_policy_attachment" "terraform_plan_readonly" {
  count = local.github_enabled ? 1 : 0

  role       = aws_iam_role.terraform_plan[0].name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "terraform_plan_state" {
  count = local.github_enabled ? 1 : 0

  name   = "state-read"
  role   = aws_iam_role.terraform_plan[0].id
  policy = data.aws_iam_policy_document.state_read.json
}

resource "aws_iam_role" "terraform_apply" {
  count = local.github_enabled ? 1 : 0

  name               = "${var.project_name}-terraform-apply"
  assume_role_policy = data.aws_iam_policy_document.github_apply_assume[0].json
}

# apply creates iam roles, vpcs, databases, ... there is no meaningful
# least-privilege policy for "all of the infrastructure". the trust policy
# (main branch only) is the control.
resource "aws_iam_role_policy_attachment" "terraform_apply_admin" {
  count = local.github_enabled ? 1 : 0

  role       = aws_iam_role.terraform_apply[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_role_policy" "terraform_apply_state" {
  count = local.github_enabled ? 1 : 0

  name   = "state-write"
  role   = aws_iam_role.terraform_apply[0].id
  policy = data.aws_iam_policy_document.state_write.json
}
