# Catan backend: Docker image for local testing and AWS ECS.
# Build context is the REPO ROOT: the uv workspace lockfile lives there and
# the image carries db/ (Alembic). Only the catan-backend workspace member is
# installed.
#   docker build -f backend/Dockerfile .
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/
RUN uv sync --frozen --no-dev --no-install-project --no-editable --package catan-backend

COPY backend/app ./backend/app
RUN uv sync --frozen --no-dev --no-editable --package catan-backend

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/false app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app backend/app ./app
COPY --chown=app:app db ./db
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000
EXPOSE 8000

# The task is the only thing with a network path to RDS, so migrations run
# here, before the server starts. `upgrade head` is idempotent, so restarts
# and Spot replacements are safe.
CMD ["sh", "-c", "alembic -c db/alembic.ini upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]
