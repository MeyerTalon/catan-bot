note to self: use small RL models (for fast inference), train N (large) in parallel, then bag them
              alternative is one big RL model, but then slow inference -> no parallelizability (?) -> long inference times -> long(er)] train times :



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
| **Game engine** (`engine/`) | Pure-Python Catan rules: `GameState`, `Action`s, and the `GameEngine` that applies them (boilerplate for now) | imported by the backend |
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
./scripts/setup.sh         # installs mise + pinned tools, syncs deps, copies .env examples, writes editor settings
```

Then, with Docker running:

```bash
mise run dev:up            # whole stack → http://localhost:8080
```

That is the production topology on your laptop, with no AWS account involved (`docker-compose.yml`):

```
browser ─▶ edge (nginx) ─┬─ /       ─▶ frontend/dist (pnpm build)
                         └─ /api/*  ─▶ backend (backend/Dockerfile: alembic, then uvicorn) ─▶ postgres:16
                                                        └─ boto3 ─▶ moto (Cognito emulator)
```

| Production | Local |
|---|---|
| CloudFront: S3 static site, `/api/*` → ALB with the prefix stripped, SPA fallback | `edge` — nginx built by `frontend/Dockerfile` with `frontend/nginx.conf`, http://localhost:8080 |
| ECS task from `backend/Dockerfile`, Alembic on start, `/health` target-group checks | `backend` — the same image and command; also http://localhost:8000 (docs at `/docs`) |
| RDS Postgres 16 | `postgres` — `localhost:5432`, user/db `catan` |
| Cognito user pool + app client (`terraform/modules/auth`) | `moto` — [moto](https://docs.getmoto.org/) `cognito-idp` on http://localhost:5001; `cognito-local-init` (`scripts/cognito-local-init.sh`) creates the same pool and client plus the dev user, writes their ids to `.generated/`, and `db-seed` logs the dev user in once so its `users` row exists |

Log in at http://localhost:8080 as the seeded dev user **`admin@example.com` / `Admin123`** (created in moto and in Postgres on every start), or sign up with any email and a prod-policy password (8+ characters, upper, lower, digit). `mise run dev:logs` follows logs; `mise run dev:down` stops the stack **and deletes its state** — moto keeps users in memory, so Postgres is reset with it rather than keeping rows for identities that no longer exist. Host ports are overridable with `EDGE_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, and `MOTO_PORT` (5001 by default because macOS AirPlay listens on 5000).

For hot reload while iterating, run the app on the host against the stack's Postgres and Cognito — `cognito-local-init` writes a ready-made env for that:

```bash
set -a; . .generated/host.env; set +a
mise run be:dev            # FastAPI with reload → http://localhost:8000
mise run fe:dev            # Vite → http://localhost:5173 (VITE_BACKEND_URL=http://localhost:8000 in frontend/.env.local)
```

The backend's `COGNITO_ENDPOINT_URL` / `COGNITO_JWKS_URL` settings are what point it at the emulator; leave them unset in `backend/.env` to use a real pool (see [backend/README.md](backend/README.md)).

## Day-to-day

| Task | Command |
|---|---|
| Sync deps after pulling | `mise run install` |
| Local stack (Docker: postgres, moto, backend, edge) | `mise run dev:up` · `mise run dev:logs` · `mise run dev:down` |
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

## Game engine

`engine/` holds the rules as a pure-Python package with no I/O; see its [README](engine/README.md). `mise run ge:check` runs ruff, mypy, and pytest for it.

## Repository layout

```
backend/        FastAPI app (app/), tests/, scripts/, Dockerfile — a member of the root uv workspace
frontend/       React + Vite app; src/api/ is generated from the backend's OpenAPI schema
db/             Alembic migrations — the source of truth for the Postgres schema
docker-compose.yml  local end-to-end stack mirroring prod (writes gitignored .generated/)
engine/         Catan rules engine (src/), tests/ — a member of the root uv workspace
terraform/      bootstrap/ (state bucket, OIDC, budget) · modules/ · envs/prod/ · ARCHITECTURE.md · README.md
docs/           MkDocs site (GitHub Pages); pages include the READMEs next to the code + a Redoc API reference
.github/        ci.yml (checks) · docs.yml (Pages) · deploy-backend / deploy-frontend / deploy / terraform (manual)
.agents/        shared agent skills and rules (symlinked into .claude/ and .cursor/); AGENTS.md is the entry point
mise.toml       pinned tool versions and every `mise run` task
scripts/        setup.sh (one-time local bootstrap) · cognito-local-init.sh (Cognito pool/client in moto for the stack)
```

Each area has its own README: [backend](backend/README.md) · [engine](engine/README.md) · [frontend](frontend/README.md) · [db](db/README.md) · [terraform](terraform/README.md).

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
