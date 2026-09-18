variable "name" {
  description = "Name prefix for database resources (e.g. catan-prod)."
  type        = string
}

variable "vpc_id" {
  description = "VPC to place the database in."
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the DB subnet group (at least two AZs). The instance is never publicly accessible."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to reach Postgres on 5432. Keys are static labels (e.g. backend); values may be unknown until apply."
  type        = map(string)
  default     = {}
}

variable "engine_version" {
  description = "Postgres major version. Minor versions auto-upgrade."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class. db.t4g.micro is the cheapest (~$12/month)."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Storage in GiB (gp3, ~$0.115/GiB/month). Backups are free up to this size."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "catan"
}

variable "username" {
  description = "Master username. The password is generated and stored in SSM Parameter Store."
  type        = string
  default     = "catan"
}

variable "backup_retention_days" {
  description = "Automated backup retention. 0 disables backups. AWS free-plan accounts reject values above 1."
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "Block terraform destroy from deleting the instance."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Keep false for anything holding real data."
  type        = bool
  default     = false
}

variable "ssl_root_cert_path" {
  description = "Path, inside the container that receives DATABASE_URL, of the RDS CA bundle. When set the URL uses sslmode=verify-full; empty keeps sslmode=require (encrypted, server not authenticated)."
  type        = string
  default     = ""
}
