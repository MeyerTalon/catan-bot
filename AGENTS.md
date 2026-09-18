# Agent instructions

Full-stack Catan app plus an LLM move-selection bot. Top-level pieces:

- `backend/` — FastAPI + SQLAlchemy + Pydantic API (`app` package) against Postgres (RDS on AWS, local Postgres in dev). Auth is proxied to Amazon Cognito (`boto3`); Cognito-JWT-protected user and session routes live here. Dockerized (`backend/Dockerfile`) for the local stack and AWS ECS Fargate.
- `frontend/` — React (Vite + TypeScript) UI; talks to the backend through the generated OpenAPI client in `frontend/src/api/`. Deployed to S3 + CloudFront.
- `db/` — Alembic migrations; source of truth for the Postgres schema (`db/README.md`).
- `docs/` + `mkdocs.yml` — MkDocs site for GitHub Pages. Pages are `include-markdown` wrappers around the READMEs, `terraform/ARCHITECTURE.md`, and this file, plus a Redoc page over `frontend/src/api/openapi.json`; edit the source files, not `docs/`. `mise run docs:serve` to preview, `docs:build` (strict) runs in CI
- `terraform/` — AWS IaC: `bootstrap/` (one-time per account: state bucket, GitHub OIDC, terraform-apply role, budget), `modules/` (network, database, auth, backend-service, static-site, deploy-role), `envs/<env>/` (composes modules; remote S3 state). Diagram + cost: `terraform/ARCHITECTURE.md`; runbook: `terraform/README.md`.
- `game-engine/` — pure-Python Catan rules engine (`game_engine` package): serialisable `GameState`, `Action` types, and a `GameEngine` that validates and applies them. No I/O; the backend stores `GameState` as JSON. Currently boilerplate — the rules are stubs.
- `docker-compose.yml` — local end-to-end stack that mirrors prod: `postgres` (16), `moto` (Cognito emulator, `cognito-idp`), `cognito-local-init` (`scripts/cognito-local-init.sh`: creates the same pool/app client as `terraform/modules/auth` plus the dev user `admin@example.com` / `Admin123`, writes ids to gitignored `.generated/`), `db-seed` (logs that user in once through the backend so its `users` row exists on every start), `backend` (the unchanged `backend/Dockerfile`), and `edge` (`frontend/Dockerfile` + `frontend/nginx.conf`: static build, `/api/*` proxied to the backend with the prefix stripped, SPA fallback — the CloudFront behaviour). `mise run dev:up|logs|down`.
- `mise.toml` — pinned tool versions and `mise run` tasks. Commit `mise.lock`.
- `scripts/` — repo-level shell scripts: `setup.sh` (one-time local bootstrap for vscode / cursor, `./scripts/setup.sh`) and `cognito-local-init.sh` (run by the compose stack).

## Environment

- Install [mise](https://mise.jdx.dev/) once (`curl https://mise.run | sh`), then from the repo root run `./scripts/setup.sh` (or `mise install` + `mise run install`) to get the pinned Python, Node, pnpm, uv, Terraform, and tflint plus project deps. Activate it in your shell (`mise activate` / `mise exec -- …`) so those shims are on PATH. Tool versions and tasks live in `mise.toml`; commit `mise.lock` when it changes. Prefer `mise run <task>` over invoking tools by hand (`mise tasks` lists them)
- Python 3.11+ and Node 22+ (pinned by mise; pnpm 11 needs Node >= 22.13)
- Python is one **uv workspace**: the repo-root `pyproject.toml` is a virtual root (no package of its own) whose members are `backend/` and `game-engine/`, so there is exactly one `uv.lock` and one `.venv`, both at the repo root. `mise run sync` (= `uv sync --frozen --all-packages --all-groups`) installs everything. Never create a `.venv` or `uv.lock` inside a member; do not activate a venv by hand or install packages with pip/conda/poetry. Cursor/VS Code workspace settings point `python.defaultInterpreterPath` at `.venv` and set `python.terminal.activateEnvironment` so new integrated terminals activate it; `mise.toml` `[env] _.python.venv` does the same for shells with `mise activate`. Do not let the mise extension overwrite the interpreter to the bare mise Python.
- Backend deps live in `backend/pyproject.toml` and game-engine deps in `game-engine/pyproject.toml`: from that directory, `uv add <package>` / `uv add --dev <package>` / `uv remove` (or `uv add --package catan-backend|catan-game-engine …` from anywhere). Both update the single root `uv.lock` — commit it. Run a member's Python through `uv run` from its directory (uv picks the member from the cwd) or the `be:*` / `ge:*` mise tasks
- Frontend dependencies are managed by pnpm from `frontend/package.json`. Use `pnpm add` / `pnpm add -D` / `pnpm remove` in `frontend/`; commit `frontend/pnpm-lock.yaml`. Do not use npm or commit `package-lock.json`
- Copy `backend/.env.example` to `backend/.env` for local backend config; never commit `.env` files or secrets
- Frontend local config goes in `frontend/.env.local` (`VITE_BACKEND_URL`; see `frontend/.env.example`)
- Backend auth is environment-aware: `ENVIRONMENT=production` makes signup require the emailed Cognito confirmation code (`/auth/confirm`); anything else auto-confirms via `admin_confirm_sign_up` because the emulator sends no mail. `CORS_ALLOWED_ORIGINS` (comma-separated) is only needed when the Vite dev server calls the backend directly (`.generated/host.env` sets it); behind the compose edge or CloudFront the API is same-origin and CORS stays off. `TRUSTED_PROXY_HOPS` tells the rate limiter how many proxies append to `X-Forwarded-For` (compose edge 1, CloudFront + ALB 2)
- Local Cognito: the backend's optional `COGNITO_ENDPOINT_URL` (boto3 `endpoint_url`) and `COGNITO_JWKS_URL` (token verification) point it at an emulator; unset means real AWS. The compose stack sets them for the `backend` container, and `.generated/host.env` (written by `cognito-local-init`) carries the host-side values for `mise run be:dev` against the containers (`set -a; . .generated/host.env; set +a`). Stack state is ephemeral by design (moto is in-memory; `dev:down` also drops Postgres so users and identities never drift apart); the seeded dev user's `sub` is deterministic (moto rng seeded before creating it), so it survives even a moto-only restart. Moto's host port defaults to 5001 (macOS AirPlay owns 5000)
- Terraform >= 1.10 (pinned by mise). `tflint` is optional and also pinned. AWS credentials go in `~/.aws/credentials` or env vars, never the repo. The only tfvars file is `terraform/bootstrap/terraform.tfvars` (copy from `.example`, gitignored); envs take their values from `locals` in `envs/<env>/main.tf`. The only secret (RDS password) is Terraform-generated into SSM Parameter Store; nothing secret passes through variables — see `terraform/README.md`

## Commands

```bash
# one-time (from repo root; vscode / cursor)
./scripts/setup.sh               # mise tools, uv + pnpm deps, env files, editor settings
# equivalent: mise install && mise run install

# backend
mise run be:dev
mise run be:check                # compile, ruff format --check, ruff check, mypy, pytest
mise run be:format               # write ruff formatting
mise run be:migrate

# local e2e stack (docker running; see docker-compose.yml)
mise run dev:up                  # cognito-local-init, build, up --wait → http://localhost:8080
mise run dev:logs
mise run dev:down                # stop and delete state (postgres + moto users)

# frontend
mise run fe:dev                  # Vite; opens Google Chrome via BROWSER env
mise run fe:check                # oxfmt --check, oxlint (warnings fail), tsc --noEmit, pnpm audit (high+)
mise run fe:format               # write oxfmt formatting
mise run fe:build
mise run api                     # export OpenAPI + regenerate TS types

# game engine
mise run ge:check                # ruff format --check, ruff check, mypy, pytest
mise run ge:format

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

Equivalent underlying commands (when not using mise tasks): `uv run …` from `backend/` or `game-engine/`, `pnpm run …` from `frontend/`, `make …` from `terraform/`. `mise tasks` lists every task.

Backend listens at `http://localhost:8000` (docs: `http://localhost:8000/docs`). Frontend Vite server is port `5173`. The compose stack serves the app at `http://localhost:8080` (API at `/api`), backend `8000`, Postgres `5432`, moto `5001` (`EDGE_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, `MOTO_PORT` override them).

## Git workflow

- Never push directly to `main`; work on a feature branch and open a PR. Nothing deploys on push: `ci.yml` (checks only) runs on PRs and on `main`; deploys and Terraform applies are manually dispatched workflows gated by the `production` GitHub environment
- Work on a feature branch (e.g. `talon/<topic>`), open a PR into `main`, and let CI run there. This applies to the `push` skill too: it pushes the current branch, so make sure you are not on `main`
- Workflows: `ci.yml` (be:check, api drift, fe:check + build, docs build, tf:check + lint, secret scan), `docs.yml` (MkDocs → GitHub Pages; the only auto-deploy, runs on `main` when docs/READMEs/OpenAPI change), `deploy-backend.yml` (pushes `:<sha>` to the immutable ECR repo, registers a task definition revision with it, rolls the service), `deploy-frontend.yml`, `deploy.yml` (both), `terraform.yml` (plan → approval → apply). Action `uses:` are pinned to commit SHAs (Dependabot bumps them); keep new ones pinned too. Never add a push/PR trigger to anything that touches AWS; never dispatch a deploy or Terraform workflow yourself — that is the user's action in the GitHub UI. `ge:check` is not wired into CI yet — run it locally

## Layout & conventions

- Backend package layout: `backend/app/{main.py, api/, core/, crud/, db/, models/, schemas/, services/}`. Routers are wired in `backend/app/api/v1/api.py`; endpoint modules live in `backend/app/api/v1/endpoints/`
- Backend tests live in `backend/tests/` (`pytest`, dev dependency). Importing `app` builds the SQLAlchemy engine, so `tests/conftest.py` sets a placeholder `DATABASE_URL`; keep unit tests free of real DB connections. Format/lint with ruff, type-check with mypy (`mise run be:check`, or `uv run ruff format|check` / `uv run mypy` from `backend/`; config in `backend/pyproject.toml`)
- Game engine layout: `game-engine/game_engine/{models.py, actions.py, board.py, engine.py}` with tests in `game-engine/tests/`; same ruff/mypy setup as the backend, configured in `game-engine/pyproject.toml` (`mise run ge:check`). Keep it free of I/O so it stays importable from the backend and any bot
- Frontend source: `frontend/src/{App.tsx, main.tsx, index.css, screens/, components/, lib/, api/}`, imported through the `@/` alias. Styling is Tailwind CSS 4 (`@tailwindcss/vite`) + shadcn/ui: `src/index.css` is the only stylesheet and holds the theme tokens (single dark "Harbor" theme — use the shadcn token classes, no hard-coded colours, no background gradients); `src/components/ui/` is CLI-generated (`pnpm dlx shadcn@latest add <component>` from `frontend/`, never hand-edit), app-specific shared components sit in `src/components/`. `src/api/openapi.json` + `schema.d.ts` are generated from the backend (`mise run api`; CI fails if stale) — never hand-edit them; `src/api/client.ts` is the typed HTTP client, `src/lib/session.ts` holds auth session state. Package manager is pnpm (`frontend/pnpm-lock.yaml`). See `frontend/README.md` § Styling
- Terraform: modules are generic (`modules/<name>/{versions,variables,main,outputs}.tf`, all inputs via variables); envs are concrete (`envs/<env>/main.tf` locals). New env = copy `envs/prod`, edit locals + `backend.hcl` key, add to the workflow matrix. Commit `.terraform.lock.hcl` for `bootstrap/` and `envs/*` only. Never commit `*.tfvars` (except `.example`), `*.tfstate`, or `*.tfplan`. Style and safety rules are in the `terraform-coding` skill — follow it for all `.tf`/`.hcl` work
- Schema changes are Alembic revisions in `db/versions/` and ship with the matching model change. Do not rely on SQLAlchemy `create_all` as the migration story
- Python style (typing, docstrings) is defined in the `python-coding` skill — follow it for all `.py` work
- Keep this AGENTS.md current: when a change makes it stale — repo structure, commands, conventions, environment, skills — update it in the same change
- Docs can lag code; when they disagree, trust the code and fix the doc in the same change

## Verification

CI (`.github/workflows/ci.yml`, on PRs and `main`) installs tools with mise, then runs `mise run be:check`, `mise run api` (OpenAPI drift), `mise run fe:check` + `fe:build`, `mise run docs:build`, `mise run tf:check` + `tf:lint`, and a secrets job (fails if a `tfplan`/`plan.txt`/`*.tfstate`/`*.tfvars`/`.env` file is tracked, then gitleaks over history). Locally, run `mise run be:check` / `mise run ge:check` / `mise run fe:check` / `mise run docs:build` for the area you touched (`mise run check` does all four); for Terraform run `mise run tf:check` (and `ENV=<env> mise run tf:plan` if credentials are available). Add lightweight `pytest` tests under `backend/tests/` or `game-engine/tests/` for critical Python (see the `python-coding` skill). For UI/layout/routing/client-state changes, exercise the flow in the browser (auth, game screen, and any shared state), not just a screenshot — `mise run dev:up` gives a prod-shaped stack with working sign-up/login and no AWS dependency. Anything that changes auth, the backend image, or the frontend build should also be checked there.

## Do not

- Invent extra Docker, CI, or packaging scaffolding unless requested — the Dockerfiles, `docker-compose.yml`, GitHub Actions, and Terraform already exist; don't expand them
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
