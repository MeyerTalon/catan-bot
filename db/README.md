# Database (Alembic)

Postgres schema for the Catan app. **Alembic** in this folder is the source of truth. Do not use SQLAlchemy `create_all` for migrations.

The FastAPI ORM models live in `backend/app/models/`. This package only stores revision files.

## Commands

From the repo root (`mise run be:migrate`) or from `backend/` with `DATABASE_URL` set:

```bash
# apply all revisions
mise run be:migrate
# or: uv run alembic -c ../db/alembic.ini upgrade head

# generate a revision after model changes
uv run alembic -c ../db/alembic.ini revision --autogenerate -m "describe the change"

# roll back one revision
uv run alembic -c ../db/alembic.ini downgrade -1
```

`env.py` reads `DATABASE_URL` via the backend settings module (RDS in production, local Postgres in development).

## Layout

```
db/
├── alembic.ini
├── env.py
├── script.py.mako
├── versions/          # revision files
└── README.md
```
