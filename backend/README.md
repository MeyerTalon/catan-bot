# Backend (FastAPI + Supabase Postgres)

FastAPI backend for the Catan app. It provides a REST API for users and game sessions, backed by Supabase Postgres via SQLAlchemy.

## Tech stack

- **Python** 3.11+
- **FastAPI** – web framework
- **SQLAlchemy 2** – ORM and Postgres connection
- **Pydantic** – request/response schemas and settings
- **Uvicorn** – ASGI server
- **python-dotenv** – load env from `backend/.env`
- **psycopg2-binary** – Postgres driver

## Structure

```
backend/
├── app/
│   ├── __init__.py    # Package entry; exports create_app
│   ├── config.py      # Settings from env (get_settings, Settings)
│   ├── db.py          # SQLAlchemy engine, Base, SessionLocal, db_session
│   ├── main.py        # FastAPI app factory (create_app), routes, run()
│   ├── models.py      # ORM: User, GameSession
│   └── schemas.py     # Pydantic: UserCreate/UserRead, GameSessionCreate/GameSessionRead
├── pyproject.toml     # Poetry project and dependencies
├── poetry.lock        # Locked dependency versions (commit to repo)
└── README.md          # This file
```

### Module roles

| File | Role |
|------|------|
| **config.py** | Loads `SUPABASE_DATABASE_URL`, optional Supabase keys, and `ENVIRONMENT` from env (and `backend/.env`). Exposes `get_settings()` returning a cached `Settings` instance. Validates that the database URL is a Postgres URL, not an HTTPS project URL. |
| **db.py** | Builds the SQLAlchemy engine from `settings.database_url`, declares `Base` for ORM models, and provides `SessionLocal` and a `db_session()` context manager for request-scoped transactions. |
| **models.py** | Defines `User` (id, email, created_at) and `GameSession` (id, user_id, state JSONB, created_at, updated_at). Aligned with `database/migrations` schema; users are linked to Supabase Auth by UUID. |
| **schemas.py** | Pydantic models for API: `UserCreate`, `UserRead`, `GameSessionCreate`, `GameSessionRead`. Used for validation and OpenAPI docs. |
| **main.py** | `create_app()` builds the FastAPI app: health check, user CRUD, and game-session endpoints. Uses `get_db()` dependency that yields a DB session. On startup, calls `Base.metadata.create_all` as a safety net (migrations remain the source of truth). |

## API overview

- **System:** `GET /health` – liveness check.
- **Users:**  
  - `POST /users` – create user (id + email, e.g. after Supabase sign-up).  
  - `GET /users/{user_id}` – get user by UUID.
- **Sessions:**  
  - `POST /users/{user_id}/sessions` – create a game session (body: `state` JSON).  
  - `GET /users/{user_id}/sessions` – list sessions for a user.

All relevant request/response bodies use the Pydantic schemas from `schemas.py`.

## Environment variables

Configure these in `backend/.env` (or your environment). The app loads `backend/.env` automatically via `config.py`.

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes | Postgres connection string (`postgresql://...` or `postgresql+psycopg2://...`). Get from Supabase: Project Settings → Database → Connection string. Must **not** be the project URL (`https://...`). |
| `SUPABASE_ANON_KEY` | No | Supabase anon key (for future server-side Supabase client use). |
| `ENVIRONMENT` | No | `development` or `production`; defaults to `development`. |

## How to use

### 1. Install dependencies with Poetry

Install [Poetry](https://python-poetry.org/docs/#installation) if needed, then from the **backend** directory:

```bash
cd backend
poetry install
```

This creates a virtualenv (by default under `backend/.venv` or in Poetry’s cache) and installs dependencies. Use `poetry run` to run commands in that environment, or `poetry shell` to activate it.

### 2. Set environment variables

Create `backend/.env` and set at least:

```bash
SUPABASE_DATABASE_URL=postgresql://user:password@host:port/dbname
```

Use the **Postgres** connection string from Supabase (Project Settings → Database), not the project URL.

### 3. Run the server

From the **backend** directory:

```bash
poetry run uvicorn app.main:create_app --factory --reload
```

Or activate the Poetry shell first, then run uvicorn:

```bash
poetry shell
uvicorn app.main:create_app --factory --reload
```

- App: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Reload: code changes restart the server automatically.

### 4. Run the backend script

From **backend**:

```bash
poetry run catan-backend
```

That invokes the `catan-backend` entry point defined in `pyproject.toml` (`app.main:run`).

## Database and migrations

- Schema is defined in **database migrations** under `database/migrations/` (see repo root and `database/README.md`). The backend does not own the schema; it matches the ORM to those migrations.
- On startup, the app calls `Base.metadata.create_all(bind=engine)` as a fallback; for real deployments, apply migrations via the Supabase CLI (e.g. `supabase db push`).

## Code style

- Google-style docstrings for modules, classes, and functions.
- Type hints on all public functions and important variables.
- Use Poetry for the backend; do not install backend deps into the global Python environment.
