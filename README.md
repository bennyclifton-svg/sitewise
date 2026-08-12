# Clerk

Clerk is the hosted SiteWise product repo: a FastAPI + React workspace where
Pi reasons behind Clerk's chat, calls Clerk tools through MCP, and drives
the Tender Comparison workflow end to end.

## Product Direction

Pi is the sole agent runtime. Governing docs:

- [Pi-only Agent Runtime](docs/plans/2026-08-04-pi-only-agent-runtime.md)
- [System architecture](docs/architecture.md)
- [Tender Comparison Module PRD](docs/plans/2026-06-11-tender-comparison-module-prd.md)

MCP, AI-SDK-compatible streaming, chat tool chips, Tender Comparison from
natural language, workspace and artefact editing, and Stripe billing are in
place. Remaining open work is live `sitewise.au` production acceptance, then
legacy PydanticAI chat cutover.

July Hermes foundation plans under `docs/plans/hermes-foundation/` are
historical only. Do not use them as current direction.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12 + FastAPI |
| Frontend | Vite + React SPA + TypeScript |
| Chat streaming | Vercel AI SDK client contract, emitted by FastAPI SSE |
| Agent runtime | Pi CLI headless via `backend/app/agent/` |
| Tool bridge | FastMCP mounted at `/mcp` |
| Database | Supabase Postgres |
| Storage | Supabase Storage for canonical uploaded project files |
| Migrations | SQLAlchemy models + Alembic |
| Retrieval | Supabase `pgvector` + Postgres full-text search |
| Auth | Supabase Auth |
| Billing | Stripe |
| Hosting | Docker + Dokploy on the `sitewise.au` VPS |
| LLM + embeddings | OpenAI and Pi platform-key routing |

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
| Pi CLI | pinned in the backend image | Headless agent turns |

Pi execution and ODL-in-Docker checks are validated on Linux/WSL2 and on the
VPS during production acceptance.

## Running Locally

Setup guides:

- [Supabase](docs/guides/supabase-setup.md)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)
- [Deployment](DEPLOYMENT.md)

Backend commands run from `backend/`.

For normal API development:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

For PDF/table extraction work, run the backend with OpenDataLoader hybrid:

```powershell
.\scripts\dev-backend-with-odl.ps1
```

That starts the OpenDataLoader hybrid server on `http://127.0.0.1:5002`, waits
for it to become healthy, configures the Clerk backend to use it, then starts
FastAPI on `http://127.0.0.1:8000`.

To start the OpenDataLoader hybrid server manually in its own terminal:

```powershell
cd backend
uv run python -m opendataloader_pdf.hybrid_server --port 5002
```

Then start FastAPI in another terminal:

```powershell
cd backend
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

The existing PydanticAI grounded-RAG chat and cockpit pages remain until live
production acceptance and the legacy cutover gate pass. Do not delete them
early; they are a deliberate safety valve.
