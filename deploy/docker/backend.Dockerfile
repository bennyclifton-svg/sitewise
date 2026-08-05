# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS pi-cli

ARG PI_CLI_VERSION=0.83.0
ARG PI_MCP_ADAPTER_VERSION=2.19.0

RUN npm install --global \
        "@earendil-works/pi-coding-agent@${PI_CLI_VERSION}" \
        "pi-mcp-adapter@${PI_MCP_ADAPTER_VERSION}" \
    && pi --version

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
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        default-jre-headless \
        git \
        libreoffice \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pi-cli /usr/local/bin/node /usr/local/bin/node
COPY --from=pi-cli /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN addgroup --system sitewise \
    && adduser --system --ingroup sitewise --home /home/sitewise sitewise \
    && mkdir -p /app/agent-workspaces \
    && ln -s ../lib/node_modules/@earendil-works/pi-coding-agent/dist/cli.js /usr/local/bin/pi \
    && pi --no-extensions \
        --extension /usr/local/lib/node_modules/pi-mcp-adapter/index.ts \
        --help | grep -F -- "--mcp-config" \
    && chown -R sitewise:sitewise /app/agent-workspaces

COPY --from=builder --chown=sitewise:sitewise /app/backend /app/backend
COPY --chown=sitewise:sitewise data/seed /app/data/seed
COPY --chown=sitewise:sitewise data/skills/reference /app/data/skills/reference
COPY --chown=sitewise:sitewise data/taxonomy /app/data/taxonomy
COPY --chown=sitewise:sitewise data/tender /app/data/tender
COPY --chown=sitewise:sitewise docs/clerk-brief.md /app/docs/clerk-brief.md

USER sitewise

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
