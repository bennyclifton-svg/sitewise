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

ARG HERMES_RELEASE_TAG=v2026.6.19

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HERMES_HOME=/opt/hermes

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        default-jre-headless \
        git \
        libreoffice \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/hermes-install.sh \
    && bash /tmp/hermes-install.sh \
        --branch "${HERMES_RELEASE_TAG}" \
        --non-interactive \
        --no-skills \
    && rm /tmp/hermes-install.sh \
    && hermes --version

RUN addgroup --system sitewise \
    && adduser --system --ingroup sitewise --home /home/sitewise sitewise \
    && mkdir -p /opt/hermes /app/agent-workspaces \
    && chown -R sitewise:sitewise /opt/hermes /app/agent-workspaces

COPY --from=builder --chown=sitewise:sitewise /app/backend /app/backend

USER sitewise

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
