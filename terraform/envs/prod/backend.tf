# partial configuration: bucket/key/region live in backend.hcl so this file
# stays identical across environments. initialise with
#   terraform init -backend-config=backend.hcl
terraform {
  backend "s3" {}
}
