# Catan Backend

FastAPI backend for the Catan app. Uses **Supabase** for Postgres and authentication; the backend proxies auth and stores user profiles and game sessions in the database.

## Tech stack

- **Python 3.11+**
- **FastAPI** – API framework
- **SQLAlchemy 2** – ORM and migrations (tables created via `create_all` on startup)
- **Postgres** – via Supabase (connection string in `SUPABASE_DATABASE_URL`)
- **Supabase Auth** – login/signup proxied through the backend using `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- **Poetry** – dependency and virtualenv management

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
│   ├── db/                  # engine, session, init_db
│   ├── models/              # SQLAlchemy models (User, GameSession)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # auth_service, user_service, game_service
│   ├── middleware/          # CORS, etc.
│   └── utils/               # constants, helpers
├── Dockerfile               # Docker image for local and Render
├── docker-compose.yml       # Local: docker compose up
├── .dockerignore
├── pyproject.toml           # Poetry config and scripts (catan-backend)
└── README.md                # This file
```

## Current functionality

### Health

- **`GET /health`** – Liveness check; returns `{"status": "ok"}`.

### Auth (Supabase proxy)

- **`POST /auth/login`** – Log in with `email` and `password`. Proxies to Supabase Auth; returns session/token payload. Requires `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- **`POST /auth/signup`** – Sign up with `email`, `password`, and optional `username`. Proxies to Supabase Auth; returns session or confirmation payload.

### Users

- **`POST /users`** – Create an application user profile (body: `id` [UUID], `email`). `id` should match the Supabase auth user id; backend trusts Supabase for auth. Fails if the user already exists.
- **`GET /users/{user_id}`** – Get a user by UUID. Returns `id`, `email`, `created_at`.

### Game sessions

- **`POST /users/{user_id}/sessions`** – Create a game session for a user. Body can include optional `state` (JSON object) for Catan game state. Returns the created session (id, user_id, created_at, updated_at, state).
- **`GET /users/{user_id}/sessions`** – List game sessions for a user, newest first. Returns a list of session objects.

User and game data are stored in Postgres. `User` has a one-to-many relationship with `GameSession`; deleting a user cascades to their sessions.

### Admin

- **`/admin`** – Router is mounted but has no endpoints yet; placeholder for future admin-only routes.

## Configuration

Create a `backend/.env` file (or set environment variables). The app loads `backend/.env` automatically.

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes | Postgres connection string (e.g. `postgresql://...` or `postgresql+psycopg2://...`). Not the Supabase project HTTPS URL. From Supabase: Project Settings → Database → Connection string. |
| `SUPABASE_URL` | For auth | Supabase project URL (e.g. `https://xxx.supabase.co`). Needed for login/signup. |
| `SUPABASE_ANON_KEY` | For auth | Supabase anon/public key. Needed for login/signup. |
| `ENVIRONMENT` | No | `development` (default) or `production`. |

If auth endpoints are called without `SUPABASE_URL` / `SUPABASE_ANON_KEY`, the backend returns 503.

## Running locally

From the repo root:

1. **Install Poetry** if needed: <https://python-poetry.org/docs/#installation>
2. **Create and use the environment:**
   ```bash
   cd backend
   poetry install
   ```
3. **Set `SUPABASE_DATABASE_URL`** (and optionally `SUPABASE_URL`, `SUPABASE_ANON_KEY`) in `backend/.env`.
4. **Run the server:**
   ```bash
   poetry run uvicorn app.main:create_app --factory --reload
   ```
   Or use the script:
   ```bash
   poetry run catan-backend
   ```
   Server runs at **http://0.0.0.0:8000**. Interactive API docs: **http://localhost:8000/docs**.

## Docker (local testing)

Build and run the backend in a container. The image uses `PORT=8000` by default; Render overrides `PORT` at runtime.

**Using Docker Compose (recommended for local):**

```bash
cd backend
# Ensure backend/.env exists with SUPABASE_DATABASE_URL, etc.
docker compose up --build
```

API: **http://localhost:8000**, docs: **http://localhost:8000/docs**.

**Using Docker directly:**

```bash
# From repo root; build context is backend/
docker build -f backend/Dockerfile -t catan-backend backend
docker run --rm -p 8000:8000 --env-file backend/.env -e PORT=8000 catan-backend
```

## Deploying to Render

The repo includes a **Render Blueprint** at the repo root: `render.yaml`. It defines a Docker-based web service that builds from `backend/Dockerfile` with build context `backend/`.

1. **Connect the repo** to Render and create a new Blueprint (Infrastructure as Code) from `render.yaml`, or create a Web Service and set:
   - **Runtime**: Docker
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Docker Build Context**: `backend`
2. **Set environment variables** in the Render dashboard for the service:
   - `SUPABASE_DATABASE_URL` (required)
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY` (required for auth)
   - Optionally `ENVIRONMENT=production`
3. Render sets `PORT` automatically; the Dockerfile CMD uses it for uvicorn. The service health check uses `GET /health`.

## Updating dependencies

- Edit `pyproject.toml`, then from `backend/`: `poetry lock` (if deps changed), then `poetry install`.
- If the environment is broken, remove the Poetry venv and run `poetry install` again from `backend/`.
