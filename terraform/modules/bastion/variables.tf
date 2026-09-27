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
  description = "EC2 instance class; must be x86_64 to match the AMI. t3.micro (~$8/month) is the cheapest type a free-plan account will actually launch; a port forward needs nothing more."
  type        = string
  default     = "t3.micro"

  validation {
    condition     = !can(regex("^[a-z]+[0-9]+g", var.instance_type))
    error_message = "instance_type must be an x86_64 class such as t3.micro; the AMI is x86_64, and free-plan accounts reject Graviton (t4g) regardless."
  }
}
