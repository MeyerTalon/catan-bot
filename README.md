# catan-bot (full-stack)

Full-stack Catan app with:

- **Backend**: FastAPI + SQLAlchemy + Pydantic (Python) using **RDS Postgres**. Auth is Amazon Cognito, proxied through the API. Docker image runs on **AWS ECS**.
- **Frontend**: React (Vite) with types generated from the backend OpenAPI schema. Static hosting is **S3 + CloudFront**.
- **CI/CD**: GitHub Actions — tests, OpenAPI type check, Alembic migrations, ECR/ECS deploy, S3/CloudFront deploy on pushes to `main`.

## Repo layout

- `backend/` – FastAPI app (`app` package) with SQLAlchemy models and Pydantic schemas; Dockerized for local runs and AWS ECS.
- `frontend/` – React (Vite) app. API client and types live in `src/api/` (generated from OpenAPI). pnpm for packages.
- `db/` – Alembic migrations (source of truth for the Postgres schema).
- `terraform/` – AWS IaC (bootstrap + reusable modules + per-env stacks: VPC, RDS, ECS Fargate, ALB, S3/CloudFront). See `terraform/README.md`.
- `mise.toml` – pinned tool versions (Python, Node, pnpm, uv, Terraform, tflint) and `mise run` tasks.
- `setup.sh` – one-time local bootstrap for vscode / cursor.
- `.github/workflows/ci-cd.yml` – CI/CD for tests, migrations, and AWS deploys.

## Setup

From the repo root in vscode / cursor:

```bash
./setup.sh
```

Installs [mise](https://mise.jdx.dev/) if needed, pins tools from `mise.toml`, syncs the backend and bot uv environments, installs frontend pnpm deps, copies env examples when missing, and writes `.vscode/` workspace settings (Python interpreter = `backend/.venv`). Then fill in `backend/.env` and run `mise run be:dev` / `mise run fe:dev`.

## Backend (FastAPI + RDS + Cognito)

- Package: `app`
- Entry point: `app.main:create_app`
- Schema: Alembic in `db/` (`uv run alembic -c ../db/alembic.ini upgrade head` from `backend/`)
- OpenAPI export: `uv run python scripts/export_openapi.py` from `backend/`

From the repo root:

```bash
./setup.sh
mise run be:dev
```

See `backend/README.md` for env vars (`DATABASE_URL`, `COGNITO_*`) and endpoint docs.

## Frontend (React + OpenAPI client)

```bash
./setup.sh
mise run fe:dev
```

Local env (`frontend/.env.local`): `VITE_BACKEND_URL=http://localhost:8000`.

After backend API changes:

```bash
mise run api
```

## Database (Alembic)

Revisions live in `db/versions/`. See `db/README.md`.

```bash
mise run be:migrate
```

## CI/CD (GitHub Actions + AWS)

Workflow: `.github/workflows/ci-cd.yml`

On push to `main`: compile/test backend, regenerate OpenAPI types and fail if they drifted, build the frontend, run Alembic against RDS, push the backend image to ECR, update ECS, sync `frontend/dist` to S3, invalidate CloudFront.

### Required GitHub secrets

| Secret | Purpose |
|--------|---------|
| `AWS_ROLE_ARN` | IAM role for GitHub OIDC (`terraform output github_deploy_role_arn` once `github_repository` is set). |
| `AWS_REGION` | e.g. `us-west-2` |
| `DATABASE_URL` | RDS connection string for Alembic |
| `ECR_REPOSITORY` | Full ECR repo URI |
| `ECS_CLUSTER` | ECS cluster name |
| `ECS_SERVICE` | ECS service name |
| `FRONTEND_BUCKET` | S3 bucket for the Vite build |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution id |
| `VITE_BACKEND_URL` | Public backend origin baked into the frontend build |

Cognito user pool id/client id are backend runtime env (ECS task), not frontend secrets.

# catan-bot

LLM-driven Catan bot that uses `gpt-oss` via [Ollama](https://ollama.com/) to choose moves from a structured game state.

The project is written in Python. Tool versions and tasks are managed with [mise](https://mise.jdx.dev/); Python packages use [uv](https://docs.astral.sh/uv/).

## Prerequisites

- **mise** (`curl https://mise.run | sh`, then `mise install` in this repo)
- **Ollama** installed locally and running
  - Install Ollama from the official site.
  - Make sure the `gpt-oss` model is available:
    - `ollama pull gpt-oss`
  - Run the Ollama server (if it is not already running in the background):
    - `ollama serve`

By default, this project expects Ollama's OpenAI-compatible HTTP API to be available at `http://localhost:11434`.

## Setup

From the project root:

```bash
mise install
mise run bot:sync
```

## Running the bot (sample game state)

Once Ollama is running with the `gpt-oss` model available:

```bash
mise run bot:choose-move
```

This will:

- Build a small sample Catan game state in code.
- Send that `GameState` (as JSON) to `gpt-oss` via Ollama's `/v1/chat/completions` endpoint.
- Expect a structured `ModelMoveResponse` JSON object in return.
- Print the model's reasoning and the chosen action.

The CLI command has a `--no-sample` flag reserved for future integration with a real game engine or external state source.
