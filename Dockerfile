# ---- Builder stage: resolve + install the locked dependency set ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, cached separately from application code so an
# app-only change doesn't invalidate this (slow) layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY . .
RUN uv sync --locked --no-dev

# ---- Runtime stage: slim image, no uv/build toolchain ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 8001

# Migrations run once per deploy in CI (a step before this image is
# deployed), not once per container cold start. Every instance just starts
# the app.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
