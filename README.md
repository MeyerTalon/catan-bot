<h1 align="center">catan-bot</h1>

<p align="center">
  A full-stack Settlers of Catan app — FastAPI + React on AWS — plus an LLM bot that picks moves from a structured game state.
</p>

<p align="center">
  <a href="https://github.com/MeyerTalon/catan-bot/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MeyerTalon/catan-bot/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MeyerTalon/catan-bot/actions/workflows/docs.yml"><img alt="Docs" src="https://github.com/MeyerTalon/catan-bot/actions/workflows/docs.yml/badge.svg"></a>
  <a href="https://meyertalon.github.io/catan-bot/"><img alt="Documentation" src="https://img.shields.io/badge/docs-github%20pages-deeporange"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
</p>

<p align="center">
  <a href="https://meyertalon.github.io/catan-bot/">Documentation</a> ·
  <a href="https://meyertalon.github.io/catan-bot/api/">API reference</a> ·
  <a href="terraform/ARCHITECTURE.md">Architecture &amp; cost</a> ·
  <a href="AGENTS.md">Agent instructions</a>
</p>

---

## What's inside

| Piece | Stack | Runs on |
|---|---|---|
| **Backend** (`backend/`) | FastAPI · SQLAlchemy 2 · Pydantic · Alembic · boto3 (Cognito) | ECS Fargate behind an ALB |
| **Frontend** (`frontend/`) | React 18 · Vite · TypeScript · typed client generated from the backend's OpenAPI schema | S3 + CloudFront |
| **Database** (`db/`) | Postgres 16, schema owned by Alembic migrations | RDS `db.t4g.micro` |
| **Auth** | Amazon Cognito user pool, proxied through the API (sign-up, login, refresh) | Cognito |
| **Bot** (`catan_bot/`) | Typer CLI that sends a `GameState` to `gpt-oss` via Ollama and gets a structured `ModelMoveResponse` back | your laptop |
| **Infra** (`terraform/`) | Terraform ≥ 1.10, reusable modules + per-env stacks, remote S3 state | AWS, ≈ $44/month idle |

```
browser ─HTTPS─▶ CloudFront ─┬─ /       ─▶ S3 (React build)
                             └─ /api/*  ─▶ ALB ─▶ ECS Fargate (FastAPI) ─▶ RDS Postgres
                                                        └─ boto3 ─▶ Cognito
```

One HTTPS hostname serves both the app and the API, so there is no CORS and no certificate to manage. Full diagram and per-resource cost: [terraform/ARCHITECTURE.md](terraform/ARCHITECTURE.md).

## Quick start

Everything is pinned and driven by [mise](https://mise.jdx.dev/) — one Python env ([uv](https://docs.astral.sh/uv/) workspace), one Node env ([pnpm](https://pnpm.io/)), Terraform, and tflint all at the versions in `mise.toml`.

```bash
git clone https://github.com/MeyerTalon/catan-bot.git && cd catan-bot
./setup.sh                 # installs mise + pinned tools, syncs deps, copies .env examples, writes editor settings
```

Then:

1. Start a local Postgres, e.g. `docker run -d --name catan-pg -e POSTGRES_USER=catan -e POSTGRES_PASSWORD=password -e POSTGRES_DB=catan -p 5432:5432 postgres:16`
2. Fill in `backend/.env` — `DATABASE_URL` (above) and the Cognito pool/client IDs (there is no local Cognito; use the prod pool from `terraform output` or one you create by hand).
3. Run it:

```bash
mise run be:migrate        # alembic upgrade head
mise run be:dev            # FastAPI with reload → http://localhost:8000 (docs at /docs)
mise run fe:dev            # Vite → http://localhost:5173
```

## Day-to-day

| Task | Command |
|---|---|
| Sync deps after pulling | `mise run install` |
| Backend server / migrations | `mise run be:dev` · `mise run be:migrate` |
| Backend checks (compile, ruff, mypy, pytest) | `mise run be:check` |
| Frontend dev server | `mise run fe:dev` |
| Frontend checks (oxfmt, oxlint, tsc) | `mise run fe:check` · `mise run fe:format` to fix formatting |
| Regenerate the TS client after an API change | `mise run api` (CI fails if `frontend/src/api/` is stale) |
| New migration after a model change | `cd backend && uv run alembic -c ../db/alembic.ini revision --autogenerate -m "…"` |
| Add a dependency | `cd backend && uv add <pkg>` · `cd frontend && pnpm add <pkg>` · `uv add <pkg>` (bot, repo root) |
| Docs site preview | `mise run docs:serve` → http://127.0.0.1:8001 |
| Terraform | `mise run tf:check` · `ENV=prod mise run tf:plan` |
| Everything CI runs | `mise run check` |

`mise tasks` lists them all.

## Running the bot

Needs [Ollama](https://ollama.com/) running locally with the `gpt-oss` model pulled (`ollama pull gpt-oss`, API at `http://localhost:11434`).

```bash
mise run bot:choose-move
```

Builds a small sample `GameState`, sends it to the model, and prints the model's reasoning and chosen action as a validated `ModelMoveResponse`. The state and response models live in `catan_bot/models.py`.

## Repository layout

```
backend/        FastAPI app (app/), tests/, scripts/, Dockerfile — a member of the root uv workspace
frontend/       React + Vite app; src/api/ is generated from the backend's OpenAPI schema
db/             Alembic migrations — the source of truth for the Postgres schema
catan_bot/      the LLM bot CLI (root package of the uv workspace)
terraform/      bootstrap/ (state bucket, OIDC, budget) · modules/ · envs/prod/ · ARCHITECTURE.md · README.md
docs/           MkDocs site (GitHub Pages); pages include the READMEs next to the code + a Redoc API reference
.github/        ci.yml (checks) · docs.yml (Pages) · deploy-backend / deploy-frontend / deploy / terraform (manual)
.agents/        shared agent skills and rules (symlinked into .claude/ and .cursor/); AGENTS.md is the entry point
mise.toml       pinned tool versions and every `mise run` task
setup.sh        one-time local bootstrap
```

Each area has its own README: [backend](backend/README.md) · [frontend](frontend/README.md) · [db](db/README.md) · [terraform](terraform/README.md).

## Deploying

Nothing deploys to AWS on push. Checks run automatically; shipping is a deliberate click in the Actions tab, gated by the `production` GitHub environment (branch-restricted to `main`, reviewer approval) and authenticated to AWS with OIDC — no long-lived keys anywhere.

| Workflow | Trigger | What it does |
|---|---|---|
| **CI** (`ci.yml`) | pull requests, pushes to `main` | backend checks, OpenAPI drift, frontend checks + build, docs build, Terraform fmt/validate/lint |
| **Docs** (`docs.yml`) | pushes to `main` touching docs, READMEs, or the OpenAPI schema | MkDocs → GitHub Pages |
| **Deploy backend** | manual | build image → ECR → roll the ECS service (migrations run inside the container) |
| **Deploy frontend** | manual | Vite build → S3 → CloudFront invalidation |
| **Deploy all** | manual | backend, then frontend |
| **Terraform** | manual | `plan`, then `apply` of that exact plan after approval |

First-time AWS bring-up and the GitHub environment/variable setup are in [terraform/README.md](terraform/README.md).

## License

[Apache 2.0](LICENSE)
