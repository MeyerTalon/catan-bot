variable "name" {
  description = "Name prefix for database resources (e.g. catan-prod)."
  type        = string
}

variable "vpc_id" {
  description = "VPC to place the database in."
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for the DB subnet group (at least two AZs)."
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to reach Postgres on 5432 (e.g. the backend service SG)."
  type        = list(string)
  default     = []
}

variable "engine_version" {
  description = "Postgres major version. Minor versions auto-upgrade."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Initial storage in GiB (gp3)."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Upper bound for storage autoscaling in GiB. Set equal to allocated_storage to disable."
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "catan"
}

variable "username" {
  description = "Master username. The password is generated and stored in Secrets Manager."
  type        = string
  default     = "catan"
}

variable "multi_az" {
  description = "Run a standby in a second AZ. Roughly doubles the instance cost."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention. 0 disables backups."
  type        = number
  default     = 7
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

variable "apply_immediately" {
  description = "Apply modifications immediately instead of in the next maintenance window."
  type        = bool
  default     = false
}
