# Phase 6 Round Trip

Date: 2026-07-04

Status: green.

## Implemented

- Added traversal-safe project workspace path resolution in
  `backend/app/agent/workspace_paths.py`.
- Moved Hermes chat turns to the project-scoped scratch root:
  `AGENT_WORKSPACE_ROOT/{project_id}/`.
- Added MCP workspace tools:
  - `list_workspace`
  - `read_workspace_file`
  - `write_workspace_file`
- Changed draft edit saves from in-place updates to new `draft_artifacts`
  versions.
- Kept uploaded source-document paths read-only through MCP workspace writes.
- Kept artefact paths database-backed: agent reads return the latest draft
  version, and agent writes to existing artefact paths create a new draft
  version.
- Added a focused frontend editor test proving the panel renders the returned
  draft version after save.

## Verification

- `uv run pytest tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/inbox tests/evidence -q`:
  103 passed, 2 skipped.
- `uv run ruff check app/agent app/api app/database app/mcp_bridge tests/agent tests/mcp_bridge tests/test_project_draft_versioning.py tests/inbox tests/evidence`:
  passed.
- `npm test`: 9 test files passed, 22 tests passed.
- `npm run build`: passed.

## Gate

Green.

The verification covers the required round trip:

- Agent-scoped workspace paths cannot traverse outside the project root.
- Agent scratch read/write/list works through MCP with a project-scoped turn
  token.
- Cross-project tokens and traversal attempts are rejected.
- In-app draft save creates a new version and leaves the previous draft row
  readable by id.
- Reopened editor state renders the returned draft version.
- Agent reads against an artefact workspace path return the latest
  `draft_artifacts` version.
- Agent writes against an existing artefact workspace path create a new
  `draft_artifacts` version.
- Uploaded source-document workspace paths are read-only from the workspace
  write tool.

