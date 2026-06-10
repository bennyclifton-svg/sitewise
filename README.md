# Clerk

An internal AI workspace for SiteWise project teams: project-scoped chat, grounded citations, cockpit workflows, and auditable draft artefacts.

## Product Direction

The accepted migration document is [Clerk Practice Intelligence Integration PRD](docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md).

Clerk is the canonical hosted product repo. Practice Intelligence is source material for cockpit and workflow behavior, and Hermes is retired as a separate runtime once Clerk reaches workflow parity. The first integrated workflow path is Create PMP in the project cockpit.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python + FastAPI |
| Frontend | Vite + React SPA + TypeScript |
| Database | Supabase Postgres (users, chats, source documents, chunks, projects, drafts) |
| Migrations | SQLAlchemy models + Alembic |
| Retrieval | Supabase `pgvector` + Postgres full-text search |
| Auth | Supabase Auth (email only) |
| Hosting | VPS/Dokploy path for `sitewise.au` |
| LLM + embeddings | OpenAI |

## Repo Layout

```text
clerk/
|-- AGENTS.md
|-- README.md
|-- data/
|-- docs/
|   |-- guides/
|   |-- issues/
|   `-- plans/
|-- backend/
`-- frontend/
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| --- | --- | --- | --- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + data tooling | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need Supabase and OpenAI credentials for the hosted app.

## Running Locally

Setup guides:

- [Supabase](docs/guides/supabase-setup.md)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)
- [SiteWise cockpit verification](docs/guides/sitewise-cockpit-verification.md)
- [Production deployment](docs/deployment.md)
- [Integrated VPS deployment](docs/guides/vps-integrated-clerk.md)

## Local Corpus

The `data/` folder contains SiteWise seed, skills, project template material, and sample project evidence folders used by ingestion and workflow verification. Payload-heavy project files remain gitignored where configured.
