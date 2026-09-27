variable "name" {
  description = "Name prefix for bastion resources (e.g. catan-prod)."
  type        = string
}

variable "vpc_id" {
  description = "VPC to place the bastion in."
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block; the only destination the bastion may reach on 5432."
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block (e.g. 10.0.0.0/16)."
  }
}

variable "subnet_id" {
  description = "Public subnet for the instance. It needs a public IP to reach SSM without a NAT gateway or VPC endpoints."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance class; must be Graviton (arm64) to match the AMI. t4g.micro (~$6/month) is the cheapest free-tier-eligible one; a port forward needs nothing more."
  type        = string
  default     = "t4g.micro"

  validation {
    condition     = can(regex("^[a-z0-9]+g[a-z]*\\.", var.instance_type))
    error_message = "instance_type must be an arm64 (Graviton) class such as t4g.micro; the AMI is arm64."
  }
}
