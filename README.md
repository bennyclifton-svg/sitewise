# Clerk

Clerk is the hosted SiteWise product repo: a FastAPI + React workspace where
Hermes will reason behind Clerk's chat, call Clerk tools through MCP, and drive
the Tender Comparison workflow end to end.

## Product Direction

The current build direction is the Hermes Foundation sequence:

- [Hermes Foundation Phases 0-2](docs/plans/2026-07-02-hermes-foundation-phases-0-2.md)
- [Hermes Foundation Phases 3-8](docs/plans/2026-07-03-hermes-foundation-phases-3-8.md)

After Phase 2 lands, Phases 3-8 add the Hermes runtime, AI-SDK-compatible
streaming, chat tool chips, Tender Comparison from natural language, workspace
and artefact editing, Stripe billing, and the final `sitewise.au` deployment.

Tender Comparison internals are governed by the
[Tender Comparison Module PRD](docs/plans/2026-06-11-tender-comparison-module-prd.md).
The July Hermes plans supersede older migration, cockpit, local-first, and Polar
deployment plans wherever they disagree.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12 + FastAPI |
| Frontend | Vite + React SPA + TypeScript |
| Chat streaming | Vercel AI SDK client contract, emitted by FastAPI SSE |
| Agent runtime | Hermes CLI headless via `backend/app/agent/` |
| Tool bridge | FastMCP mounted at `/mcp` |
| Database | Supabase Postgres |
| Storage | Supabase Storage for canonical uploaded project files |
| Migrations | SQLAlchemy models + Alembic |
| Retrieval | Supabase `pgvector` + Postgres full-text search |
| Auth | Supabase Auth |
| Billing | Polar today; Stripe in Phase 7 |
| Hosting | Docker + Dokploy on the `sitewise.au` VPS |
| LLM + embeddings | OpenAI and Hermes platform-key routing |

## Repo Layout

```text
clerk/
|-- AGENTS.md
|-- README.md
|-- data/
|-- docs/
|   |-- guides/
|   `-- plans/
|-- backend/
`-- frontend/
```

## Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Python | 3.12+ | Backend runtime |
| uv | latest | Backend dependencies and commands |
| Node.js | 20+ | Frontend toolchain |
| pnpm | latest | Frontend package manager |
| Supabase | hosted project | Auth, Postgres, object storage |
| OpenAI | API key / platform key | Current LLM and embedding calls |

Hermes execution and ODL-in-Docker checks are validated on Linux/WSL2, then on
the VPS during Phase 8.

## Running Locally

Setup guides:

- [Supabase](docs/guides/supabase-setup.md)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)
- [Deployment](docs/deployment.md)

Backend commands run from `backend/`:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Frontend commands run from `frontend/`:

```bash
pnpm install
pnpm dev
```

## Data

The checked-in `data/` tree contains SiteWise seed/reference material, workflow
contracts, Tender Comparison seed data, project templates, and synthetic
mobilisation evidence. Large project-evidence payloads are intentionally not
part of this active context unless explicitly added for a test or fixture.

See [data/README.md](data/README.md).

## Legacy Modules

The existing PydanticAI grounded-RAG chat, Polar billing, and cockpit pages are
still live until the planned Phase 8.5 cutover. Do not delete them early; the
Hermes plan keeps them as a safety valve until the production demo passes.

