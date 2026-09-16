# Cognito user pool + app client for the backend's email/password auth flow
# (initiate_auth USER_PASSWORD_AUTH, sign_up, admin_confirm_sign_up,
# REFRESH_TOKEN_AUTH). Email is the username; the backend confirms sign-ups
# itself, so no verification email is sent.

resource "aws_cognito_user_pool" "this" {
  name = var.name

  deletion_protection = var.deletion_protection ? "ACTIVE" : "INACTIVE"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  username_configuration {
    case_sensitive = false
  }

  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  lifecycle {
    # cognito rejects schema changes after creation
    ignore_changes = [schema]
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.name}-backend"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = var.generate_client_secret

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true

  access_token_validity  = var.access_token_validity_minutes
  id_token_validity      = var.access_token_validity_minutes
  refresh_token_validity = var.refresh_token_validity_days

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

# what the backend's task role needs to call on this pool
data "aws_iam_policy_document" "backend" {
  statement {
    actions = [
      "cognito-idp:AdminConfirmSignUp",
      "cognito-idp:AdminGetUser",
    ]
    resources = [aws_cognito_user_pool.this.arn]
  }
}
