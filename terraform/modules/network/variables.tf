variable "name" {
  description = "Name prefix for all network resources (e.g. catan-prod)."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the VPC. Subnets are carved with /24 blocks."
  type        = string
  default     = "10.0.0.0/16"
}
