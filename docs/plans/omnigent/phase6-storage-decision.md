# Phase 6 Storage Decision

Date: 2026-07-04

Status: decided.

## Decision

Supabase Storage and the `workspace_files` table remain canonical for uploaded
source documents. Hermes does not receive raw filesystem access to source PDFs
or other canonical uploads.

Hermes receives a project-scoped scratch root:

```text
AGENT_WORKSPACE_ROOT/{project_id}/
```

The chat runner now uses that project root as the Hermes working directory.
MCP workspace tools resolve paths against the same root with traversal, absolute
path, drive-prefix, colon-segment, and symlink-escape checks.

Editable artefacts remain canonical in `draft_artifacts`. Scratch files are
disposable. When an MCP workspace read targets an artefact workspace path, Clerk
returns the latest draft version from the database. When an MCP workspace write
targets an existing artefact workspace path, Clerk creates a new
`draft_artifacts` version instead of writing a raw scratch shadow. Writes to
uploaded source-document workspace paths are rejected as read-only.

## Rationale

- Source documents are already stored and authorized through Supabase Storage.
- Hermes can discover and reason over source documents through document MCP
  tools such as search and tender document listing.
- Agent scratch files are useful for temporary working notes, but they are not a
  system of record.
- Keeping `draft_artifacts` authoritative avoids drift between an in-app edit
  and what the agent sees on the next turn.

## Path Rules

- `notes/report.md` resolves inside `AGENT_WORKSPACE_ROOT/{project_id}/`.
- `../../secret`, absolute paths, Windows drive paths, UNC paths, colon
  segments, and symlink escapes are rejected.
- One project id cannot resolve into another project's root.
- Root listing is allowed and creates the project scratch root on demand.

