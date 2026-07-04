# Phase 6: Workspaces And Artefacts

## Objective

Complete safe workspace/document/artefact access for users and Hermes while
keeping Supabase Storage canonical for source documents.

## Storage Decision

- Source documents remain in Supabase Storage and `workspace_files`.
- Hermes never gets raw filesystem access to canonical uploaded PDFs.
- Hermes reads source documents through MCP tools.
- Hermes gets a scoped scratch directory under
  `AGENT_WORKSPACE_ROOT/{project_id}/`.
- `draft_artifacts` remains authoritative for editable artefacts.
- Scratch files are disposable and may be rehydrated from DB/storage on demand.

## Implementation Changes

- Add `backend/app/agent/workspace_paths.py` with traversal-safe resolution.
- Add MCP file tools for scoped scratch access: `list_workspace`,
  `read_workspace_file`, and `write_workspace_file`.
- Complete any missing document repository APIs for list, upload, download, and
  delete, reusing Supabase Storage helpers.
- Make draft edit versioning an explicit behavior change. The current
  `PATCH /projects/{project_id}/drafts/{draft_id}` edits in place; Phase 6
  should instead create a new `draft_artifacts` version, preserve provenance,
  and return the new draft.
- Keep source documents read-only. Editing a `workspace_files` source path must
  fail through the artefact edit path.
- Wire the frontend repository and draft editor to the completed APIs.

## Tests

- Normal relative scratch paths resolve inside the project root.
- Traversal, absolute paths, and symlink escapes are rejected.
- Different project ids cannot resolve into each other's tree.
- Authorized MCP scratch read/write works.
- Cross-project token and traversal attempts are rejected.
- Draft patch creates a new version and leaves the previous version readable.
- Editing a source document through the draft endpoint returns 404 or 400.
- Frontend editor save path has a focused render test.

## Gate

- Traversal/security tests pass.
- Agent creates or updates an artefact, user edits it in-app, reopened draft
  shows the edit, and the agent can read the latest version.

## Gate Result - 2026-07-04

Status: green.

Implemented and verified:

- `backend/app/agent/workspace_paths.py` resolves project-scoped scratch paths
  under `AGENT_WORKSPACE_ROOT/{project_id}/` and rejects traversal, absolute
  paths, drive paths, colon segments, and symlink escapes.
- Hermes chat turns now use the project-scoped workspace root.
- MCP tools `list_workspace`, `read_workspace_file`, and
  `write_workspace_file` are authorized by the Phase 2 turn token and use the
  traversal-safe resolver.
- `read_workspace_file` returns the latest editable artefact from
  `draft_artifacts` when the path is an artefact workspace path.
- `write_workspace_file` creates a new draft version when the path is an
  existing artefact workspace path, writes only disposable scratch files
  otherwise, and rejects uploaded source-document paths as read-only.
- `PATCH /projects/{project_id}/drafts/{draft_id}` now creates a new
  `draft_artifacts` version, preserving the previous version by id.
- The existing repository UI already covers browse/upload/download/delete
  through workspace tree, inbox upload, workspace-file download, and evidence
  delete paths.
- The draft editor save path renders the returned new draft version after save.

Verification:

- `uv run pytest tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/inbox tests/evidence -q`:
  103 passed, 2 skipped.
- `uv run ruff check app/agent app/api app/database app/mcp_bridge tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/inbox tests/evidence`:
  passed.
- `npm test`: 9 files passed, 22 tests passed.
- `npm run build`: passed.

Phase 7 may begin.
