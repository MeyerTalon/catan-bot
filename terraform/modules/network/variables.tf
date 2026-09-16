variable "name" {
  description = "Name prefix for all network resources (e.g. catan-prod)."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR for the VPC. Subnets are carved with /24 blocks."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones (one public + one private subnet each)."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 4
    error_message = "az_count must be between 2 and 4 (ALB needs at least two AZs)."
  }
}

variable "enable_nat_gateway" {
  description = "Create a single NAT gateway so private subnets get outbound internet. Costs ~$32/month; off by default (tasks run in public subnets instead)."
  type        = bool
  default     = false
}
