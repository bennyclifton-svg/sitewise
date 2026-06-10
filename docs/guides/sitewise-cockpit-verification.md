# SiteWise Cockpit Verification

Use this path after applying migrations and starting both Clerk services.

## Local Services

- Backend: run the FastAPI service with the Clerk backend environment configured.
- Frontend: run the Vite React app with `VITE_API_BASE_URL` pointing to the backend.
- Database: apply Alembic migrations through `003_sitewise_projects_and_drafts`.
- Corpus: ingest SiteWise platform knowledge before workflow verification:
  - `uv run python -m ingest run --file docs/clerk-brief.md --execute` (doctrine)
  - `uv run python -m ingest run --folder seed --execute`
  - `uv run python -m ingest run --folder skills --execute` (required for Create Cost Plan on residential archetypes)
- Ingest project evidence folders as needed for grounded drafts.

## Smoke Path

1. Sign in through Supabase email auth.
2. Confirm the home page lists at least one SiteWise project.
3. Open the project cockpit from the project list.
4. Confirm project identity, workspace path, and `archetype`, `user_role`, and `state` overlay status render in the left rail.
5. Open the evidence workspace and confirm at least one text-like project evidence preview is visible.
6. Use project chat with cross-project mode off and ask a project-specific question.
7. Inspect citations and confirm they distinguish project evidence from SiteWise platform knowledge.
8. Turn cross-project mode on and confirm the chat rail labels the broader retrieval mode.
9. Run Create PMP on a project with valid overlays and indexed project evidence.
10. Confirm the workflow trace records gate, retrieval, model, validation, and draft save events.
11. Open the PMP draft in the centre workspace and confirm version, status, timestamp, provenance, evidence refs, and context refs are visible.

## Expected Blocked State

If any required overlay is missing, blank, unsupported, or TBC, Create PMP should stop before retrieval/model execution and name the exact blocker. Project chat should remain available.
