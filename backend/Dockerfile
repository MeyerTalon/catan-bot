# Catan backend: Docker image for local testing and AWS ECS.
# Build context: backend/ (docker build -f backend/Dockerfile backend/)
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

COPY app ./app
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/false app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]
