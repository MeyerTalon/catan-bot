# One tiny EC2 instance reachable only through SSM Session Manager: no key
# pair, no inbound rules, no listening port. It exists so a laptop can open a
# port forward to RDS (`mise run db:tunnel`). The agent dials out to SSM over
# the instance's public IP, which costs $3.65/month against $21 for the three
# SSM VPC endpoints.

# x86_64 rather than arm64: free-plan accounts refuse to launch Graviton
# (t4g.*) with InvalidParameterCombination even though describe-instance-types
# reports them free-tier-eligible, so the instance type has to be t3.micro
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# ---------------------------------------------------------------------------
# iam: the agent registers with ssm through the instance profile
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume_ec2" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-bastion"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json
}

# the managed policy is exactly what the agent needs (register, messaging
# channels); it grants nothing on other aws resources
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "this" {
  name = "${var.name}-bastion"
  role = aws_iam_role.this.name
}

# ---------------------------------------------------------------------------
# network
# ---------------------------------------------------------------------------

# no ingress rule on purpose: sessions ride the agent's outbound channel
resource "aws_security_group" "this" {
  name        = "${var.name}-bastion"
  description = "Bastion; no ingress, sessions arrive through SSM"
  vpc_id      = var.vpc_id

  tags = { Name = "${var.name}-bastion" }
}

resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.this.id
  description       = "SSM agent to the ssm, ssmmessages, and ec2messages endpoints"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

# the vpc cidr rather than the database security group so this module does
# not depend on database while database depends on it for its ingress rule
resource "aws_vpc_security_group_egress_rule" "postgres" {
  security_group_id = aws_security_group.this.id
  description       = "Port-forward target: Postgres inside the VPC"
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
  cidr_ipv4         = var.vpc_cidr
}

# ---------------------------------------------------------------------------
# instance
# ---------------------------------------------------------------------------

resource "aws_instance" "this" {
  ami                         = data.aws_ssm_parameter.al2023.insecure_value
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.this.id]
  iam_instance_profile        = aws_iam_instance_profile.this.name
  associate_public_ip_address = true # outbound to ssm without a nat gateway

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  # al2023 ships the ssm agent enabled, so no user_data. pick up newer amis
  # only when the instance is recreated; otherwise every release would force
  # a replacement
  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = "${var.name}-bastion" }
}
