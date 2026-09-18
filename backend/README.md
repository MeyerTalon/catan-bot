# Catan Backend

FastAPI backend for the Catan app. Uses **RDS Postgres** (SQLAlchemy + Alembic) and **Amazon Cognito** for authentication. Login/signup are proxied through this API; user profiles and game sessions live in Postgres.

## Tech stack

- **Python 3.11+**
- **FastAPI** – API framework; `/openapi.json` is the source of truth for frontend wire types
- **SQLAlchemy 2** – ORM
- **Alembic** – schema migrations in `db/`
- **Postgres** – RDS (connection string in `DATABASE_URL`)
- **Amazon Cognito** – login/signup and JWT issuance
- **uv** – dependency management. The backend is a member of the repo-root uv workspace: one `uv.lock` and one `.venv` at the repo root (`mise run sync`); `uv run …` from `backend/` uses it
- **ruff** – formatter and linter (dev)
- **mypy** – type checker (dev)
- **pytest** – unit tests (dev)

## Project layout

```
backend/
├── app/
│   ├── main.py              # App factory, lifespan, CORS, uvicorn entrypoint
│   ├── api/
│   │   ├── deps.py          # Shared dependencies (e.g. get_db)
│   │   └── v1/
│   │       ├── api.py       # v1 router wiring
│   │       └── endpoints/   # health, auth, users, games
│   ├── core/                # config, security
│   ├── crud/                # DB operations (user, game)
│   ├── db/                  # engine, session
│   ├── models/              # SQLAlchemy models (User, GameSession)
│   ├── schemas/             # Pydantic request/response schemas
│   └── services/            # auth_service, user_service, game_service
├── scripts/
│   └── export_openapi.py    # Writes frontend/src/api/openapi.json
├── Dockerfile               # Docker image for the local stack and AWS ECS
├── pyproject.toml
└── README.md
```

## Current functionality

### Health

- **`GET /health`** – Liveness check; returns `{"status": "ok"}`.

### Auth (Cognito proxy)

- **`POST /auth/signup`** – Sign up with `email`, `password`, and optional `username`. Creates the Cognito user and returns `AuthSignupResponse`: in production `confirmation_required` is true and Cognito emails a code; in development the account is confirmed at once and `session` is set. An email that already exists gets the same answer in production, so signup cannot be used to enumerate accounts.
- **`POST /auth/confirm`** – Confirm a signup with `email` and the emailed `code`. Log in afterwards.
- **`POST /auth/resend-confirmation`** – Email a fresh code. Same response whether or not the account exists.
- **`POST /auth/login`** – Log in with `email` and `password`. Proxies to Cognito; returns `AuthSessionResponse` and upserts the `users` row (409 if the email already belongs to a row with a different id).
- **`POST /auth/refresh`** – Exchange a refresh token for a new access token.
- **`POST /auth/logout`** – Revoke a `refresh_token` (and, when an `Authorization` header is sent, sign out that access token's session). Always succeeds.

Auth routes are rate limited per client IP (10/min for credential routes, 30/min for refresh/logout; `429` with `Retry-After`). Cognito error details are logged, not returned; clients get a fixed set of safe messages.

### Users

- **`GET /users/{user_id}`** – Get a user by UUID. **Protected**. Users can only access their own profile. Rows are created by signup/login; there is no public create route.

### Game sessions

- **`POST /users/{user_id}/sessions`** – Create a game session. **Protected**.
- **`GET /users/{user_id}/sessions`** – List sessions, newest first. **Protected**.

Protected endpoints require:

```
Authorization: Bearer <cognito-access-token>
```

The backend validates the JWT against the Cognito JWKS (RS256, issuer, `exp`/`iat`/`sub` required, `token_use` must be `access`, `client_id` must be this app client — id tokens are rejected), extracts `sub`, and ensures users can only access their own resources. Request bodies over 1 MB are rejected with `413`; a game session `state` is capped at 64 KB.

## Configuration

Create a `backend/.env` file (or set environment variables). The app loads `backend/.env` automatically.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string (`postgresql://...` or `postgresql+psycopg2://...`). |
| `COGNITO_REGION` | For auth | AWS region of the user pool (default `us-west-2`). |
| `COGNITO_USER_POOL_ID` | For auth | Cognito user pool id. |
| `COGNITO_CLIENT_ID` | For auth | Cognito app client id. Enable `USER_PASSWORD_AUTH` on the client. |
| `COGNITO_CLIENT_SECRET` | If confidential client | App client secret; omit for public clients. |
| `COGNITO_ENDPOINT_URL` | No | Cognito API endpoint override for a local emulator (the compose stack sets `http://moto:5000`). Unset = real AWS. |
| `COGNITO_JWKS_URL` | No | JWKS url override for a local emulator. Unset = `<issuer>/.well-known/jwks.json` on AWS. |
| `ENVIRONMENT` | No | `development` (default) or `production`. |

Without Cognito settings, login/signup return 503 and protected routes cannot validate JWTs. boto3 signs every Cognito request, so a local emulator also needs dummy `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the environment.

## OpenAPI

The frontend generates TypeScript types from this API:

```bash
mise run be:openapi
mise run fe:generate-api
```

Commit both `frontend/src/api/openapi.json` and `frontend/src/api/schema.d.ts`. CI fails if they are stale.

## Running locally

From the repo root with [mise](https://mise.jdx.dev/) installed (`./scripts/setup.sh` from the repo root does this):

1. **Install tools and deps:**
   ```bash
   mise install
   mise run sync      # one uv env at the repo root for backend + bot
   ```
2. **Set `DATABASE_URL` and Cognito vars** in `backend/.env`.
3. **Apply migrations:**
   ```bash
   mise run be:migrate
   ```
4. **Run the server:**
   ```bash
   mise run be:dev
   ```
   Or from `backend/`: `uv run catan-backend`

   Server: **http://0.0.0.0:8000**. Docs: **http://localhost:8000/docs**. OpenAPI: **http://localhost:8000/openapi.json**.

## Quality checks

From the repo root after `mise install` / `mise run sync`:

```bash
mise run be:format          # format (single quotes, line length 88)
mise run be:lint            # ruff check
mise run be:typecheck       # mypy on `app`
mise run be:test            # pytest
mise run be:check           # all of the above plus compileall
```

CI runs `mise run be:check`.

## Docker

The repo-root `docker-compose.yml` runs this image together with Postgres, a Cognito emulator (moto), and the frontend edge — `mise run dev:up` from the repo root (see the root README). The container runs Alembic against `DATABASE_URL` and then uvicorn, exactly as ECS does.

To build or run the image on its own:

```bash
docker build -f backend/Dockerfile -t catan-backend .   # context is the repo root (image includes db/)
docker run --rm -p 8000:8000 --env-file backend/.env -e PORT=8000 catan-backend
```

## Deploying to AWS

CI on `main` builds the Docker image, pushes it to ECR, applies Alembic migrations, and force-deploys the ECS service. Infra lives in `terraform/` (not modified by this app-layer cutover). Required GitHub secrets are listed in the root README.

## Updating dependencies

- From `backend/`: `uv add <package>` for runtime deps, `uv add --dev <package>` for test/dev deps, `uv remove <package>` to drop them. Then `uv lock` is updated automatically; commit `uv.lock`.
