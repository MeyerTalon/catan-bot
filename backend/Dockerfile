# Catan backend: Docker image for local testing and Render deployment.
# Build context: backend/ (docker build -f backend/Dockerfile backend/)
FROM python:3.11-slim AS builder
WORKDIR /build

# Install build dependencies including PostgreSQL dev libraries
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and use system Python (no venv in container).
ENV POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-dev --no-interaction --no-root

# Final stage: minimal runtime image.
FROM python:3.11-slim
WORKDIR /app

# Install runtime PostgreSQL libraries
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running the app.
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/false app

# Copy installed packages from builder.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code.
COPY --chown=app:app app ./app
USER app

# Render sets PORT; default 8000 for local.
ENV PORT=8000
EXPOSE 8000

# No --reload in production; PORT is used by Render.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT}"]