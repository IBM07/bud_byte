# syntax=docker/dockerfile:1.7
# One image for every backend process: api, worker and cron jobs differ only by command.
# Build from the repo root:  docker build -f infra/Dockerfile -t budbyte-api .

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock ./
COPY services/api/pyproject.toml services/api/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package budbyte-api

COPY services/api services/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package budbyte-api --no-editable

FROM python:${PYTHON_VERSION}-slim AS runtime
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000
USER app
EXPOSE 8000
# No image-level HEALTHCHECK: the same image runs the worker and crons, which serve no HTTP.
# The api's health check (/healthz liveness, /readyz readiness) is configured on the platform.

# Default process is the API. Override for others:
#   worker: budbyte-worker      cron: budbyte-cron nightly | budbyte-cron maint
CMD ["budbyte-api"]
