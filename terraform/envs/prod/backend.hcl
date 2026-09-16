# values come from `terraform output` in terraform/bootstrap
bucket       = "catan-terraform-state-<ACCOUNT_ID>"
key          = "envs/prod/terraform.tfstate"
region       = "us-west-2"
encrypt      = true
use_lockfile = true
