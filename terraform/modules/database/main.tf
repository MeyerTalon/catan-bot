# Single RDS Postgres instance in private subnets. The master password is
# generated here and exposed only through a Secrets Manager secret whose JSON
# keys ECS can inject directly (DATABASE_URL plus the individual parts).

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
  for_each = toset(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.this.id
  description                  = "Postgres from ${each.value}"
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

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.username
  password = random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.this.id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  backup_retention_period   = var.backup_retention_days
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name}-postgres-final"
  apply_immediately         = var.apply_immediately

  tags = { Name = "${var.name}-postgres" }

  lifecycle {
    # the final snapshot name must be stable across plans
    ignore_changes = [final_snapshot_identifier]
  }
}

locals {
  connection_url = "postgresql://${var.username}:${random_password.master.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}?sslmode=require"
}

resource "aws_secretsmanager_secret" "this" {
  name        = "${var.name}/database"
  description = "Postgres credentials for ${var.name}; managed by Terraform"

  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "this" {
  secret_id = aws_secretsmanager_secret.this.id
  secret_string = jsonencode({
    DATABASE_URL = local.connection_url
    HOST         = aws_db_instance.this.address
    PORT         = tostring(aws_db_instance.this.port)
    DBNAME       = var.db_name
    USERNAME     = var.username
    PASSWORD     = random_password.master.result
  })
}
