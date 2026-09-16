# Catan Backend

FastAPI backend for the Catan app. Uses **RDS Postgres** (SQLAlchemy + Alembic) and **Amazon Cognito** for authentication. Login/signup are proxied through this API; user profiles and game sessions live in Postgres.

## Tech stack

- **Python 3.11+**
- **FastAPI** – API framework; `/openapi.json` is the source of truth for frontend wire types
- **SQLAlchemy 2** – ORM
- **Alembic** – schema migrations in `db/`
- **Postgres** – RDS (connection string in `DATABASE_URL`)
- **Amazon Cognito** – login/signup and JWT issuance
- **uv** – dependency and virtualenv management (`uv sync`, `uv run`, `uv add`)
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
│   │       └── endpoints/   # health, auth, users, games, admin
│   ├── core/                # config, security, logging, exceptions
│   ├── crud/                # DB operations (user, game)
│   ├── db/                  # engine, session
│   ├── models/              # SQLAlchemy models (User, GameSession)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # auth_service, user_service, game_service
│   ├── middleware/          # CORS, etc.
│   └── utils/               # constants, helpers
├── scripts/
│   └── export_openapi.py    # Writes frontend/src/api/openapi.json
├── Dockerfile               # Docker image for local and AWS ECS
├── docker-compose.yml       # Local: docker compose up
├── pyproject.toml
├── uv.lock
└── README.md
```

## Current functionality

### Health

- **`GET /health`** – Liveness check; returns `{"status": "ok"}`.

### Auth (Cognito proxy)

- **`POST /auth/login`** – Log in with `email` and `password`. Proxies to Cognito; returns `AuthSessionResponse`.
- **`POST /auth/signup`** – Sign up with `email`, `password`, and optional `username`. Creates the Cognito user, upserts a `users` row, returns a session when confirmation succeeds.
- **`POST /auth/refresh`** – Exchange a refresh token for a new access token.

### Users

- **`POST /users`** – Create an application user profile (body: `id` [UUID], `email`). `id` should match the Cognito `sub`. Fails if the user already exists. **Public**. Signup already upserts a profile.
- **`GET /users/{user_id}`** – Get a user by UUID. **Protected**. Users can only access their own profile.

### Game sessions

- **`POST /users/{user_id}/sessions`** – Create a game session. **Protected**.
- **`GET /users/{user_id}/sessions`** – List sessions, newest first. **Protected**.

Protected endpoints require:

```
Authorization: Bearer <cognito-access-token>
```

The backend validates the JWT against the Cognito JWKS, extracts `sub`, and ensures users can only access their own resources.

## Configuration

Create a `backend/.env` file (or set environment variables). The app loads `backend/.env` automatically.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string (`postgresql://...` or `postgresql+psycopg2://...`). |
| `COGNITO_REGION` | For auth | AWS region of the user pool (default `us-west-2`). |
| `COGNITO_USER_POOL_ID` | For auth | Cognito user pool id. |
| `COGNITO_CLIENT_ID` | For auth | Cognito app client id. Enable `USER_PASSWORD_AUTH` on the client. |
| `COGNITO_CLIENT_SECRET` | If confidential client | App client secret; omit for public clients. |
| `ENVIRONMENT` | No | `development` (default) or `production`. |

Without Cognito settings, login/signup return 503 and protected routes cannot validate JWTs.

## OpenAPI

The frontend generates TypeScript types from this API:

```bash
mise run be:openapi
mise run fe:generate-api
```

Commit both `frontend/src/api/openapi.json` and `frontend/src/api/schema.d.ts`. CI fails if they are stale.

## Running locally

From the repo root with [mise](https://mise.jdx.dev/) installed (`./setup.sh` from the repo root does this):

1. **Install tools and deps:**
   ```bash
   mise install
   mise run be:sync
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

From the repo root after `mise install` / `mise run be:sync`:

```bash
mise run be:format          # format (single quotes, line length 88)
mise run be:lint            # ruff check
mise run be:typecheck       # mypy on `app`
mise run be:test            # pytest
mise run be:check           # all of the above plus compileall
```

CI runs `mise run be:check`.

## Docker (local testing)

```bash
cd backend
docker compose up --build
```

API: **http://localhost:8000**.

```bash
docker build -f backend/Dockerfile -t catan-backend backend
docker run --rm -p 8000:8000 --env-file backend/.env -e PORT=8000 catan-backend
```

## Deploying to AWS

CI on `main` builds the Docker image, pushes it to ECR, applies Alembic migrations, and force-deploys the ECS service. Infra lives in `terraform/` (not modified by this app-layer cutover). Required GitHub secrets are listed in the root README.

## Updating dependencies

- From `backend/`: `uv add <package>` for runtime deps, `uv add --dev <package>` for test/dev deps, `uv remove <package>` to drop them. Then `uv lock` is updated automatically; commit `uv.lock`.
