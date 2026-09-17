---
name: terraform-coding
description: >-
  Applies this repo's Terraform conventions when writing, editing, reviewing,
  or planning AWS infrastructure under terraform/. Trigger whenever the user
  invokes "/terraform-coding", asks to add/change/review infrastructure, AWS
  resources, IaC, modules, environments, remote state, or CI for Terraform,
  or otherwise works in .tf/.hcl files — including implicitly. Compose with
  other skills (e.g. concise) as needed.
---

# Terraform Coding

Write Terraform that fits the `terraform/` layout: reusable modules with no environment knowledge, thin per-environment roots that compose them, and a one-time `bootstrap/` stack for account-level foundations. Read `terraform/README.md` before changing anything structural.

## Layout rules

- **Modules are generic, envs are specific.** `modules/<name>/` never hardcodes an environment, region, account id, or project name — everything comes in through `variables.tf`. `envs/<env>/main.tf` holds the concrete values in its `locals` block and wires modules together. If you find yourself adding an `if environment == "prod"` inside a module, the value belongs in the env instead.
- **One resource family per module.** `network`, `database`, `auth`, `backend-service`, `static-site`, `deploy-role`. Add a new module when a new independently-deployable thing appears (a worker, a queue, a second service), not for a single extra resource — those go in the module that owns the thing they serve.
- **Every module has the same five files.** `versions.tf` (required_version + providers), `variables.tf`, `main.tf`, `outputs.tf`, plus more `*.tf` only when `main.tf` would exceed ~300 lines (split by resource family, e.g. `iam.tf`, `alb.tf`).
- **Bootstrap is append-only.** `bootstrap/` uses local state and is applied by a human once. Only add account-singletons there (state bucket, OIDC provider, org-wide roles). Never put application resources in it.
- **Env roots own no logic.** `envs/<env>/` is `versions.tf`, `providers.tf`, `backend.tf` + `backend.hcl`, `variables.tf` (deploy-time overrides only, e.g. image tag), `main.tf`, `outputs.tf`. Adding a resource directly in an env root is acceptable only for env-specific glue (like attaching one module's policy output to another's role); anything reusable goes in a module.
- **New environment = copy `envs/prod`, edit `locals` and `backend.hcl` `key`, register in `.github/workflows/terraform.yml` matrix.** Nothing else should need to change.

## Style rules

- **Pin versions.** `required_version = ">= 1.10"` (S3 native locking), `aws = "~> 6.0"`, `random = "~> 3.6"`. Commit `.terraform.lock.hcl` for root stacks (`bootstrap/`, `envs/*`); never for `modules/*`.
- **Name resources `this` when the module has one of them** (`aws_vpc.this`, `aws_db_instance.this`); use descriptive names only to disambiguate siblings (`aws_security_group.alb` vs `.tasks`). Physical names are `"${var.name}-<suffix>"`, where `var.name` is `<project>-<env>[-<component>]`.
- **`for_each` over `count` for collections;** `count = condition ? 1 : 0` only for optional singletons, and reference them as `resource.name[0]` behind the same condition.
- **Every variable and output has a `description`.** Variables that shape cost or safety (`desired_count`, `instance_class`, `deletion_protection`, `skip_final_snapshot`) say so in the description. Add `validation` blocks for values that would only fail at apply time (regions, ARN formats, ranges).
- **Sensitive data:** mark outputs `sensitive = true`; never accept secrets as module variables. Secrets Terraform generates (the RDS password) go into an SSM `SecureString` parameter (free) and ECS reads them by ARN via `secrets = [{ name, value_from }]`; IDs that are not secret (Cognito pool/client IDs) go in `environment = {}`. If a third-party secret is ever needed, create only the parameter in Terraform with a placeholder, write the value out-of-band, and put `lifecycle { ignore_changes = [value] }` on it.
- **Prefer `aws_iam_policy_document` data sources over `jsonencode` for IAM.** Use the `aws_vpc_security_group_ingress_rule` / `_egress_rule` resources, not inline `ingress {}` blocks.
- **Comments explain why, in lowercase**, matching the repo's Python convention (`# no NAT by default to keep idle cost low`). Section dividers (`# ----- iam -----`) are fine in long files. Never restate what the resource block already says.
- **Tags come from `default_tags` on the provider** (Project, Environment, ManagedBy). Only add a `Name` tag on resources where the console shows it.

## Safety rules

- **Never run `terraform apply` or `destroy` yourself** unless the user explicitly asks in that message. `plan` is fine (it is read-only with `-lock=false`). Show the plan summary and stop.
- **Never set `deletion_protection = false`, `skip_final_snapshot = true`, `force_destroy = true`, or `prevent_destroy = false` on a prod resource** without calling it out in the reply. These are the only lines between a typo and data loss.
- **No secrets in `.tfvars`, locals, or outputs without `sensitive`.** `*.tfvars` is gitignored except `*.example`; `backend.hcl` is committed because it holds only bucket coordinates.
- **Changes that force replacement** (renaming a resource, changing `identifier`, `name`, subnet group, `family`) must be flagged explicitly; use `moved {}` blocks for pure renames so state follows the code.
- **Do not add a NAT gateway, private subnets, multi-AZ, autoscaling, Secrets Manager, Container Insights, WAF, or larger instance classes** as a side effect of another change; each is a deliberate cost decision the user makes in `envs/<env>/main.tf`. The target is the ~$44/month stack in `terraform/ARCHITECTURE.md`; every new resource needs a line in its cost table.

## Verification (always, before reporting done)

```bash
mise run tf:check       # terraform fmt -check + validate every stack and module
mise run tf:lint        # tflint (installed by mise)
```

Both run without AWS credentials. Equivalent: `make check` / `make lint` from `terraform/`. If the change touches an env root and credentials are available, also run `ENV=<env> mise run tf:plan` and summarise adds/changes/destroys. CI (`.github/workflows/terraform.yml`) runs the same checks on every PR touching `terraform/`; the apply job on `main` runs only when `AWS_TERRAFORM_APPLY_ROLE_ARN` is set.

## Anti-goals

Don't add abstraction for its own sake (a `modules/tags` module, wrapper modules around single resources, a `common` variables module). Don't reach for community modules (`terraform-aws-modules/*`) for things the local modules already cover — consistency beats feature count here. Don't turn `envs/prod/main.tf` into a variables-driven template; literal values in `locals` are the point. Don't "fix" the cost defaults upward.

## Examples

- "add a Redis cache for the backend" → new `modules/cache/` (ElastiCache + SG + subnet group, ingress from a `allowed_security_group_ids` list), wired in `envs/prod/main.tf`, endpoint passed to `module.backend.environment`, `make check` clean, reply notes the monthly cost.
- "give the site a custom domain" → add `aliases` + `acm_certificate_arn` (us-east-1) variables to `static-site` and a Route 53 record in the env; note the $0.50/month zone in the reply. The API needs nothing: it already rides the same distribution under `/api`.
- "add a staging env" → follow *Adding an environment* in `terraform/README.md`; shrink sizing; add `staging` to the workflow matrix.
- "why is the plan replacing the RDS instance?" → diagnose (`identifier`/subnet group/engine major change), propose a `moved {}` or explain the destroy, never apply.
