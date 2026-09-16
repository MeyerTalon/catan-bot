# Least-privilege IAM role that GitHub Actions assumes via OIDC to ship the
# application (push images, roll the ECS service, sync the frontend). It has no
# rights to change infrastructure; Terraform CI uses the roles from bootstrap.

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [for ref in var.github_refs : "repo:${var.github_repository}:ref:${ref}"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = var.name
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "deploy" {
  dynamic "statement" {
    for_each = length(var.ecr_repository_arns) > 0 ? [1] : []
    content {
      sid       = "EcrAuth"
      actions   = ["ecr:GetAuthorizationToken"]
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = length(var.ecr_repository_arns) > 0 ? [1] : []
    content {
      sid = "EcrPush"
      actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
      ]
      resources = var.ecr_repository_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.ecs_service_arns) > 0 ? [1] : []
    content {
      sid = "EcsDeploy"
      actions = [
        "ecs:DescribeServices",
        "ecs:UpdateService",
      ]
      resources = var.ecs_service_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.ecs_service_arns) > 0 ? [1] : []
    content {
      sid = "EcsTaskDefinitions"
      actions = [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
      ]
      resources = ["*"] # these actions do not support resource-level permissions
    }
  }

  dynamic "statement" {
    for_each = length(var.ecs_task_definition_arns) > 0 ? [1] : []
    content {
      sid       = "EcsRunTask"
      actions   = ["ecs:RunTask"]
      resources = var.ecs_task_definition_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.ecs_task_definition_arns) > 0 ? [1] : []
    content {
      sid       = "EcsDescribeTasks"
      actions   = ["ecs:DescribeTasks"]
      resources = ["*"] # task arns are not known ahead of time
    }
  }

  dynamic "statement" {
    for_each = length(var.ecs_task_role_arns) > 0 ? [1] : []
    content {
      sid       = "PassEcsRoles"
      actions   = ["iam:PassRole"]
      resources = var.ecs_task_role_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.s3_bucket_arns) > 0 ? [1] : []
    content {
      sid = "FrontendSync"
      actions = [
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
      ]
      resources = concat(var.s3_bucket_arns, [for arn in var.s3_bucket_arns : "${arn}/*"])
    }
  }

  dynamic "statement" {
    for_each = length(var.cloudfront_distribution_arns) > 0 ? [1] : []
    content {
      sid       = "CloudFrontInvalidate"
      actions   = ["cloudfront:CreateInvalidation"]
      resources = var.cloudfront_distribution_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.cloudfront_distribution_arns) > 0 ? [1] : []
    content {
      sid       = "CloudFrontList"
      actions   = ["cloudfront:ListDistributions"]
      resources = ["*"] # list actions are account-wide; used to find the distribution id by comment
    }
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "deploy"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.deploy.json
}
