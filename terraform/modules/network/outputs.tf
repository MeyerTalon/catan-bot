output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR block."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs, ordered by AZ."
  value       = [for az in local.azs : aws_subnet.public[az].id]
}

output "private_subnet_ids" {
  description = "Private subnet IDs, ordered by AZ."
  value       = [for az in local.azs : aws_subnet.private[az].id]
}

output "nat_gateway_enabled" {
  description = "Whether private subnets have outbound internet via NAT."
  value       = var.enable_nat_gateway
}
