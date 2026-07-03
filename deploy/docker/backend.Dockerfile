# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app/backend

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

WORKDIR /app/backend

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system sitewise && adduser --system --ingroup sitewise sitewise

COPY --from=builder --chown=sitewise:sitewise /app/backend /app/backend

USER sitewise

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
