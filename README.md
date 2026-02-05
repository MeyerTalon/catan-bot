# catan-bot (full-stack)

Full-stack Catan app with:

- **Backend**: FastAPI + SQLAlchemy + Pydantic (Python) using a **Supabase Postgres** database.
- **Frontend**: React (Vite) deployed to **Vercel**, using **Supabase Auth** for login/sign up.
- **CI/CD**: GitHub Actions pipeline that runs tests, applies Supabase migrations, and triggers a Vercel deployment on pushes to `main`.

## Repo layout

- `backend/` – FastAPI app (`app` package) with SQLAlchemy models and Pydantic schemas.
- `frontend/` – React (Vite) app with a Supabase-powered login/sign up screen.
- `supabase/` – Database migrations (SQL) for Supabase Postgres.
- `.github/workflows/ci-cd.yml` – CI/CD workflow for tests, migrations, and Vercel deployment.

## Backend (FastAPI + Supabase Postgres)

- Package: `app`
- Entry point: `app.main:create_app`
- Key files:
  - `backend/app/config.py` – loads `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, etc.
  - `backend/app/db.py` – SQLAlchemy engine/session setup.
  - `backend/app/models.py` – `User` and `GameSession` ORM models.
  - `backend/app/schemas.py` – Pydantic schemas for users and game sessions.
  - `backend/app/main.py` – FastAPI app with basic health, user, and session endpoints.

### Backend setup with `.venv`

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install --upgrade pip
cd backend
pip install -e .
```

Then run the backend:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"  # Supabase DB URL
uvicorn app.main:create_app --factory --reload
```

## Frontend (React + Supabase Auth, Vite, Vercel)

- Production deployment (live): `https://catan-bot.vercel.app/`

- React app under `frontend/`:
  - `src/lib/supabaseClient.ts` – Supabase JS client.
  - `src/screens/AuthScreen.tsx` – login / sign up UI.
  - `src/main.tsx` – renders `AuthScreen`.

### Frontend env variables

Configure in Vercel (and `.env.local` for local dev):

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

### Running frontend locally

```bash
cd frontend
npm install
npm run dev
```

## Supabase migrations

- `supabase/migrations/0001_init.sql` contains initial `users` and `game_sessions` tables.
- Use the Supabase CLI (and `SUPABASE_DB_URL`) to push migrations, e.g.:

```bash
supabase db push --db-url "$SUPABASE_DB_URL"
```

For a more complete workflow (local Supabase, diff-based migrations, and helper
commands), see `supabase/README.md` and the `Makefile` targets:

```bash
make supabase-start    # run local Supabase stack
make db-reset-local    # recreate local DB from migrations
make db-push-remote    # apply migrations to remote DB via SUPABASE_DB_URL
```

## CI/CD (GitHub Actions + Vercel + Supabase)

Workflow: `.github/workflows/ci-cd.yml`

- On push to `main`:
  - Runs backend tests (Python) in `backend/`.
  - Builds frontend (Node) in `frontend/`.
  - Applies Supabase migrations via `supabase db push` (CLI uses `supabase/` symlink to `database/`).
  - Deploys the frontend to Vercel (production).

### Required GitHub secrets

- `SUPABASE_ACCESS_TOKEN` – for Supabase CLI (if needed).
- `SUPABASE_DB_URL` – database URL for migrations.
- `VERCEL_TOKEN` – Vercel deploy token.
- Any other Vercel-related environment (e.g. `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`) if required in your Vercel setup.

# catan-bot

LLM-driven Catan bot that uses `gpt-oss` via [Ollama](https://ollama.com/) to choose moves from a structured game state.

The project is written in Python and is designed to be run inside a dedicated Conda environment (see `environment.yml`).

## Prerequisites

- **Conda** (e.g. Miniconda or Anaconda)
- **Python** 3.11 (handled by the Conda env)
- **Ollama** installed locally and running
  - Install Ollama from the official site.
  - Make sure the `gpt-oss` model is available:
    - `ollama pull gpt-oss`
  - Run the Ollama server (if it is not already running in the background):
    - `ollama serve`

By default, this project expects Ollama's OpenAI-compatible HTTP API to be available at `http://localhost:11434`.

## Setup (Conda environment)

From the project root:

```bash
conda env create -f environment.yml -n catan-bot
conda activate catan-bot
```

If the environment already exists and you update dependencies, you can run:

```bash
conda env update -f environment.yml -n catan-bot
```

You can also install the package in editable mode (optional but recommended for development):

```bash
pip install -e .
```

## Running the bot (sample game state)

Once the environment is active and Ollama is running with the `gpt-oss` model available:

```bash
conda activate catan-bot
catan-bot choose-move
```

This will:

- Build a small sample Catan game state in code.
- Send that `GameState` (as JSON) to `gpt-oss` via Ollama's `/v1/chat/completions` endpoint.
- Expect a structured `ModelMoveResponse` JSON object in return.
- Print the model's reasoning and the chosen action.

The CLI command has a `--no-sample` flag reserved for future integration with a real game engine or external state source.

