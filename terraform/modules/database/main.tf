# Single-AZ RDS Postgres. The master password is generated here and exposed
# only through an SSM SecureString parameter (free tier) that ECS injects as
# DATABASE_URL. The instance has no public IP; only the allowed security
# groups can reach it inside the VPC.

resource "random_password" "master" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.name}-db" }
}

resource "aws_security_group" "this" {
  name        = "${var.name}-db"
  description = "Postgres; ingress only from allowed security groups"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.name}-db" }
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  for_each = var.allowed_security_group_ids

  security_group_id            = aws_security_group.this.id
  description                  = "Postgres from ${each.key}"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = each.value
}

resource "aws_db_instance" "this" {
  identifier = "${var.name}-postgres"

  engine                     = "postgres"
  engine_version             = var.engine_version
  auto_minor_version_upgrade = true
  instance_class             = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period   = var.backup_retention_days
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name}-postgres-final"

  # performance insights is on by default for new instances; keep it off so
  # nothing accrues past the free 7-day retention
  performance_insights_enabled = false

  tags = { Name = "${var.name}-postgres" }
}

locals {
  connection_url = "postgresql://${var.username}:${random_password.master.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}?sslmode=require"
}

resource "aws_ssm_parameter" "database_url" {
  name        = "/${var.name}/DATABASE_URL"
  description = "Postgres connection string for ${var.name}; managed by Terraform"
  type        = "SecureString"
  value       = local.connection_url
}
