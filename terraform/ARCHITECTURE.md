# Architecture

Single environment, single AZ where AWS allows it, no autoscaling, no NAT, no private subnets, no Secrets Manager. Prices are us-west-2, on-demand, 730 h/month, ~zero traffic.

```
                         ┌──────────────────────────── AWS account ────────────────────────────┐
                         │                                                                      │
 browser ──HTTPS──▶ CloudFront ──┬─ /       ──▶ S3 bucket (React build, private, OAC)           │
                    (free TLS,   │                                                              │
                     *.cloudfront.net)                                                          │
                                 └─ /api/*  ──HTTP──▶ ALB :80 ─────▶ ECS service (Fargate Spot)  │
                                                      │ SG: CloudFront   1 task 0.25 vCPU/0.5 GB │
                                                      │ prefix list only  public IP, :8000      │
                                                      │                        │      │         │
                         ┌────────── VPC 10.0.0.0/16 ─┼────────────────────────┼──────┼───────┐ │
                         │  public subnet AZ-a        │   public subnet AZ-b   │      │       │ │
                         │  (ALB, task, RDS)          │   (ALB, RDS standby*)  │      │       │ │
                         │                            └── target group ◀───────┘      │       │ │
                         │                                                            ▼       │ │
                         │                     RDS Postgres db.t4g.micro (private, SG: task)  │ │
                         └────────────────────────────────────────────────────────────────────┘ │
                                                                                 │              │
                                                    Cognito user pool ◀── boto3 ─┘ (sign-up,    │
                                                    (no VPC)                        login,      │
                                                                                    refresh)    │
                         │  ECR (image)  CloudWatch Logs  SSM Parameter Store (DATABASE_URL)  IAM │
                         └──────────────────────────────────────────────────────────────────────┘
 * second subnet exists only because ALB and RDS subnet groups require two AZs; nothing runs there.
```

Request path: browser → CloudFront → (static from S3 | `/api/*` to ALB over HTTP inside AWS) → task → RDS. Auth calls go task → Cognito over the public AWS API. Migrations run in the container entrypoint (`alembic upgrade head` then `uvicorn`), so nothing outside the VPC needs a DB route.

## Resources and monthly cost

| Layer | Resource | Why | $/month |
|---|---|---|---|
| Frontend | CloudFront distribution (+ OAC, CloudFront Function that strips `/api`) | TLS, CDN, serves `/` from S3 and `/api/*` from ALB | 0.00 (1 TB + 10 M req + 2 M function calls always free) |
| Frontend | S3 bucket (+ policy, public-access block) | React build | ~0.01 |
| Edge→API | ALB (+ target group, HTTP listener, SG) | stable endpoint for the task; only route CloudFront can use | 16.43 |
| Edge→API | 2 × public IPv4 on the ALB (one per AZ, mandatory) | | 7.30 |
| API | ECS cluster + task definition + service | schedules the container | 0.00 |
| API | Fargate Spot, 1 task, 0.25 vCPU / 0.5 GB | runs FastAPI | ~2.70 (9.01 on-demand) |
| API | 1 × public IPv4 on the task | outbound to ECR, Cognito, SSM without a NAT ($32) | 3.65 |
| API | ECR repository (<500 MB) | image | ~0.05 |
| API | CloudWatch log group (<5 GB) | container logs | 0.00 |
| API | SSM Parameter Store SecureString | `DATABASE_URL` for the task | 0.00 (standard tier) |
| API | IAM roles (execution, task) | pull image, read parameter, call Cognito | 0.00 |
| DB | RDS PostgreSQL 16 `db.t4g.micro`, single-AZ | | 11.68 (0.00 while stopped, max 7 days) |
| DB | 20 GB gp3 storage | | 2.30 |
| DB | automated backups, 1 day | | 0.00 (free-plan max; 7 days is rejected) |
| DB | DB subnet group, SG, default KMS key | | 0.00 |
| Auth | Cognito user pool + app client | ≤10 000 MAU | 0.00 |
| Network | VPC, 2 public subnets, IGW, route table, SGs | | 0.00 |
| Bootstrap | S3 state bucket, GitHub OIDC provider, 2 IAM roles, AWS Budget alert | | ~0.00 |
| | **Total** | | **≈ 44** |

- ≈ **$32** with RDS stopped between sessions; ≈ **$21** if the ALB were replaced by API Gateway + VPC link (rejected for simplicity).
- Fixed floor regardless of traffic: ALB + IPv4 ≈ $27. RDS ≈ $14. Everything else rounds to zero.
- $200 new-account credits cover ≈ 4.5 months. After credits, only CloudFront, S3, Cognito, Logs stay free.

## Not included, on purpose

NAT gateway ($32), Multi-AZ RDS (2×), private subnets, autoscaling, Secrets Manager ($0.40/secret), Container Insights, WAF ($5 + $1/rule), Route 53 / custom domain ($0.50/zone), ACM cert on the ALB (needs a domain), VPC endpoints ($7 each). Add any of them later in `envs/prod/main.tf`; none require re-architecting.

## Terraform shape

`bootstrap/` (state bucket, OIDC, apply role, budget) · `modules/{network, database, auth, backend-service, static-site, deploy-role}` · `envs/prod/` (locals + module calls). ≈ 50 resources total, all validated with `make check`.
