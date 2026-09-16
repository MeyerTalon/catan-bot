terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # intentionally local: this stack creates the bucket the other stacks use.
  # keep bootstrap/terraform.tfstate somewhere safe (it holds no secrets).
}
