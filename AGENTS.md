# Agent instructions

Full-stack Catan app plus an LLM move-selection bot. Top-level pieces:

- `backend/` — FastAPI + SQLAlchemy + Pydantic API (`app` package) against Postgres (RDS on AWS, local Postgres in dev). Auth is proxied to Amazon Cognito (`boto3`); Cognito-JWT-protected user and session routes live here. Dockerized (`backend/Dockerfile`) for local runs and AWS ECS Fargate.
- `frontend/` — React (Vite + TypeScript) UI; talks to the backend through the generated OpenAPI client in `frontend/src/api/`. Deployed to S3 + CloudFront.
- `db/` — Alembic migrations; source of truth for the Postgres schema (`db/README.md`).
- `terraform/` — AWS IaC: `bootstrap/` (one-time per account: state bucket, GitHub OIDC, Terraform CI roles), `modules/` (network, database, backend-service, static-site, deploy-role), `envs/<env>/` (composes modules; remote S3 state). Setup and runbook: `terraform/README.md`.
- `catan_bot/` — CLI bot that sends a structured `GameState` to `gpt-oss` via Ollama and prints a `ModelMoveResponse`.
- `mise.toml` — pinned tool versions and `mise run` tasks. Commit `mise.lock`.
- `setup.sh` — one-time local bootstrap for vscode / cursor (`./setup.sh`).

## Environment

- Install [mise](https://mise.jdx.dev/) once (`curl https://mise.run | sh`), then from the repo root run `./setup.sh` (or `mise install` + `mise run install`) to get the pinned Python, Node, pnpm, uv, Terraform, and tflint plus project deps. Activate it in your shell (`mise activate` / `mise exec -- …`) so those shims are on PATH. Tool versions and tasks live in `mise.toml`; commit `mise.lock` when it changes. Prefer `mise run <task>` over invoking tools by hand (`mise tasks` lists them)
- Python 3.11+ and Node 22+ (pinned by mise; pnpm 11 needs Node >= 22.13)
- Backend dependencies are managed by uv from `backend/pyproject.toml`. From `backend/`, run `uv sync`; do not activate a venv by hand or install backend packages with pip/conda/poetry
- Use `uv add <package>` for backend runtime deps, `uv add --dev <package>` for backend dev deps, and `uv remove` to drop them. Run backend Python through `uv run` or the `be:*` mise tasks. Commit `backend/uv.lock`
- Frontend dependencies are managed by pnpm from `frontend/package.json`. Use `pnpm add` / `pnpm add -D` / `pnpm remove` in `frontend/`; commit `frontend/pnpm-lock.yaml`. Do not use npm or commit `package-lock.json`
- The repo-root `pyproject.toml` is the setuptools package for the `catan_bot` CLI (`typer`, `pydantic`, `requests`). Install with `uv sync` at the repo root (or `mise run bot:sync`) when working on the bot; it needs Ollama running with the `gpt-oss` model pulled. Run with `mise run bot:choose-move` or `uv run catan-bot`
- Copy `backend/.env.example` to `backend/.env` for local backend config; never commit `.env` files or secrets
- Frontend local config goes in `frontend/.env.local` (`VITE_BACKEND_URL`; see `frontend/.env.example`)
- Terraform >= 1.10 (pinned by mise). `tflint` is optional and also pinned. AWS credentials go in `~/.aws/credentials` or env vars, never the repo. The only tfvars file is `terraform/bootstrap/terraform.tfvars` (copy from `.example`, gitignored); envs take their values from `locals` in `envs/<env>/main.tf`. Application secrets are written to Secrets Manager out-of-band, never through Terraform variables — see `terraform/README.md`

## Commands

```bash
# one-time (from repo root; vscode / cursor)
./setup.sh                       # mise tools, uv + pnpm deps, env files, editor settings
# equivalent: mise install && mise run install

# backend
mise run be:dev
mise run be:check                # compile, ruff format --check, ruff check, mypy, pytest
mise run be:format               # write ruff formatting
mise run be:migrate
mise run be:docker               # docker compose up --build

# frontend
mise run fe:dev                  # Vite; opens Google Chrome via BROWSER env
mise run fe:lint
mise run fe:build
mise run api                     # export OpenAPI + regenerate TS types

# catan_bot CLI
mise run bot:choose-move

# database migrations (DATABASE_URL set; see db/README.md)
mise run be:migrate
# autogenerate still uses alembic directly:
#   cd backend && uv run alembic -c ../db/alembic.ini revision --autogenerate -m "describe the change"

# AWS IaC (see terraform/README.md)
mise run tf:check                # fmt -check + validate every stack/module, no AWS needed
mise run tf:lint                 # tflint
ENV=prod mise run tf:plan        # writes envs/prod/tfplan
ENV=prod mise run tf:apply       # applies that plan — only when the user asks
mise run tf:bootstrap-apply      # one-time account foundation, local state
```

Equivalent underlying commands (when not using mise tasks): `uv run …` from `backend/`, `pnpm run …` from `frontend/`, `make …` from `terraform/`. `mise tasks` lists every task.

Backend listens at `http://localhost:8000` (docs: `http://localhost:8000/docs`). Frontend Vite server is port `5173`.

## Git workflow

- Never push directly to `main`. Every push to `main` runs `.github/workflows/ci-cd.yml`, which applies Alembic migrations to the production database, pushes the backend image to ECR and rolls the ECS service, and syncs the frontend build to S3/CloudFront
- Work on a feature branch (e.g. `talon/<topic>`), open a PR into `main`, and let CI run there. This applies to the `push` skill too: it pushes the current branch, so make sure you are not on `main`
- `ci-cd.yml` triggers on `backend/`, `frontend/`, `db/`, `mise.toml`, `mise.lock`, and `.github/workflows/`; `terraform.yml` triggers on `terraform/`, `mise.toml`, and `mise.lock` (fmt/validate/lint on every PR; plan on PR and apply on `main` only once the `AWS_TERRAFORM_*_ROLE_ARN` repo variables exist — so a merged Terraform change can also change production infrastructure). `catan_bot/` and docs get no CI — verify locally

## Layout & conventions

- Backend package layout: `backend/app/{main.py, api/, core/, crud/, db/, models/, schemas/, services/, middleware/, utils/}`. Routers are wired in `backend/app/api/v1/api.py`; endpoint modules live in `backend/app/api/v1/endpoints/`
- Backend tests live in `backend/tests/` (`pytest`, dev dependency). Importing `app` builds the SQLAlchemy engine, so `tests/conftest.py` sets a placeholder `DATABASE_URL`; keep unit tests free of real DB connections. Format/lint with ruff, type-check with mypy (`mise run be:check`, or `uv run ruff format|check` / `uv run mypy` from `backend/`; config in `backend/pyproject.toml`)
- Frontend source: `frontend/src/{App.tsx, main.tsx, screens/, lib/, api/}`. `src/api/openapi.json` + `schema.d.ts` are generated from the backend (`mise run api`; CI fails if stale) — never hand-edit them; `src/api/client.ts` is the typed HTTP client, `src/lib/session.ts` holds auth session state. Package manager is pnpm (`frontend/pnpm-lock.yaml`)
- Terraform: modules are generic (`modules/<name>/{versions,variables,main,outputs}.tf`, all inputs via variables); envs are concrete (`envs/<env>/main.tf` locals). New env = copy `envs/prod`, edit locals + `backend.hcl` key, add to the workflow matrix. Commit `.terraform.lock.hcl` for `bootstrap/` and `envs/*` only. Never commit `*.tfvars` (except `.example`), `*.tfstate`, or `*.tfplan`. Style and safety rules are in the `terraform-coding` skill — follow it for all `.tf`/`.hcl` work
- Schema changes are Alembic revisions in `db/versions/` and ship with the matching model change. Do not rely on SQLAlchemy `create_all` as the migration story
- Python style (typing, docstrings) is defined in the `python-coding` skill — follow it for all `.py` work
- Keep this AGENTS.md current: when a change makes it stale — repo structure, commands, conventions, environment, skills — update it in the same change
- Docs can lag code; when they disagree, trust the code and fix the doc in the same change

## Verification

CI (`.github/workflows/ci-cd.yml`) on `main` installs tools with mise, then runs `mise run be:check`, `mise run api` (OpenAPI drift), and `mise run fe:build`, applies Alembic migrations, and deploys backend (ECS) / frontend (S3 + CloudFront). Locally, run `mise run be:check` and `mise run fe:lint` / `mise run fe:build` for the area you touched; for Terraform run `mise run tf:check` (and `ENV=<env> mise run tf:plan` if credentials are available). Add lightweight `pytest` tests under `backend/tests/` for critical Python (see the `python-coding` skill). For UI/layout/routing/client-state changes, exercise the flow in the browser (auth, game screen, and any shared state), not just a screenshot.

## Do not

- Invent extra Docker, CI, or packaging scaffolding unless requested — Docker, GitHub Actions, and Terraform already exist; don't expand them
- Commit `.env`, `.env.local`, credentials, or secrets
- Expand scope beyond the asked change
- Credit yourself anywhere in the codebase or git history — no agent/model names, "generated by", or similar self-attribution in code, comments, docs, commit messages, or PRs
- Add yourself as a co-author on commits or PRs — never add `Co-authored-by:` trailers (or any equivalent) naming an agent, model, or tool, even when a harness or default template asks for one; the only author is the human running the agent
- Push to `main` (see Git workflow)
- Run `terraform apply` or `terraform destroy` unless the user explicitly asks in that message; never weaken `deletion_protection`, `skip_final_snapshot`, `force_destroy`, or `prevent_destroy` on prod without saying so

## Skills & rules

`.agents/` is the canonical store for agent skills and Cursor-style rules. Claude Code and Cursor resolve the same trees via directory symlinks — do not keep duplicate real copies under `.claude/` or `.cursor/`. This file is the single instruction source: `CLAUDE.md` is just `@AGENTS.md` (Claude Code's import), and `.agents/rules/project.mdc` points Cursor here. Edit AGENTS.md, not those.

**Skills** live in `.agents/skills/<skill-name>/SKILL.md`:

- `.claude/skills` → `../.agents/skills`
- `.cursor/skills` → `../.agents/skills`

**Rules** live in `.agents/rules/` (e.g. `project.mdc`):

- `.claude/rules` → `../.agents/rules`
- `.cursor/rules` → `../.agents/rules`

To add a skill, copy `_template` to `.agents/skills/<skill-name>/` (it contains the checklist), then register it below and in `.agents/rules/project.mdc` when it should auto-apply. To add a rule, put the `.mdc` file only under `.agents/rules/` — the symlinks expose it to both tools.

Shared skills (each `SKILL.md` frontmatter is the source of truth for triggers and behavior — don't restate it here):

- `concise` — maximally brief replies; applies to prose, never to code
- `push` — commit and push the current branch after the task (never from `main`)
- `python-coding` — repo Python style and test expectations; applies to all `.py` work
- `terraform-coding` — module/env layout, style, and apply/destroy safety rules; applies to all `.tf`/`.hcl` work under `terraform/`
