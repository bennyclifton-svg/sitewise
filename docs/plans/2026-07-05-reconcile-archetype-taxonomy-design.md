# Reconcile legacy `archetype` with the Class/Work-type taxonomy

## Problem

The Project Profile panel shows two competing controls for "what kind of
project is this": a legacy **Archetype** dropdown (5 flat values: new-dwelling,
renovation, multi-dwelling, ancillary, small-commercial) and the PMP 2.0
**Class + Work type** taxonomy picker (6 classes x 5 work types + subclass/
scale/complexity). They can be set independently and disagree with each
other.

`archetype` was meant to be retired from the product UI once the taxonomy
landed (see `docs/plans/pmp2/02-phase-2-project-setup-ux.md` Task 2.2: "do
not expose a legacy archetype UX"; decision D9 in
`docs/plans/2026-07-05-pmp2-live-interactive-pmp.md`: "archetype retained
only as compatibility/test-fixture fallback, not a product migration
target"). The Archetype dropdown currently in `ProjectProfilePanel` is drift
from that decision — it was reintroduced (uncommitted, in this working tree)
to work around the overlay gate, which still hard-requires `archetype` and
had no way to be satisfied post-creation without it.

Everywhere else in the codebase already treats the taxonomy as authoritative
when present, falling back to `archetype` only when taxonomy is absent
(`archetype_bridge.effective_taxonomy()`, `knowledge_catalog.
select_required_paths()`/`list_platform_knowledge()`). The overlay gate
(`gate.py::overlay_status()`) is the one place that doesn't follow this
pattern — it checks `archetype` alone, ignoring `building_class`/`work_type`
entirely.

## Decisions

- **Gate rule**: satisfied by (`building_class` AND `work_type` both set) OR
  legacy `archetype` in the 5 supported values. Both paths report readiness;
  neither is required to migrate the other.
- **Legacy fallback stays**: old/seeded/test projects that only have
  `archetype` (e.g. the auto-seeded default project every new user gets)
  keep working unblocked with zero migration.
- **UI**: remove the Archetype dropdown entirely from Project Profile and
  Create Project. Nothing in the frontend sets `archetype` going forward.
  Role and State remain their own fields (different axis, unaffected).
- **Schema/DB unchanged**: `archetype` column, `SUPPORTED_ARCHETYPES`, and
  the `archetype` field on `CreateProjectRequest`/`PatchProjectRequest`
  all stay, for legacy/test-fixture compatibility. Only its status as a
  *live, gate-relevant, user-facing* concept goes away.

## Changes

### Backend

**`app/sitewise/gate.py`**
- `overlay_status()` gains `building_class: str | None = None`,
  `work_type: str | None = None` (defaulted so existing call sites that only
  pass `archetype` keep compiling/working).
- Taxonomy check: ready if (`building_class` and `work_type` both non-empty)
  OR (`archetype` cleaned and in `SUPPORTED_ARCHETYPES`). If neither path
  holds, emit `missing` issues on `building_class` and `work_type`
  individually (not a generic "archetype" bucket) — these map 1:1 to the
  two dropdowns in the UI.

**Six call sites pass the two new fields through** (`project.building_class`,
`project.work_type`):
- `app/database/projects.py::project_overlay_summary()`
- `app/workflows/create_pmp.py::run_create_pmp_workflow()`
- `app/workflows/create_cost_plan.py`
- `app/workflows/sort_files.py`
- `app/workflows/update_pmp.py`
- `app/mcp_bridge/server.py::list_platform_knowledge` (the gate check inside
  the MCP tool)

**Bug fix — MCP tool crash**: `mcp_bridge/server.py::list_platform_knowledge`
calls `select_required_paths(archetype=project.archetype, user_role=...)`
and `catalog_platform_knowledge(archetype=project.archetype, ...)` *without*
`building_class`/`work_type`. Once a project has taxonomy set but no legacy
archetype (the normal case after the dropdown is removed), `select_required_
paths` falls into its legacy branch, looks for an entry keyed
`archetype: None`, finds none, and raises `ValueError`. Fix: resolve
`building_class`/`work_type` via `archetype_bridge.effective_taxonomy(project)`
before both calls, mirroring what `pmp_sources.py::required_platform_paths()`
already does correctly.

**`app/agent/turn_context.py`**: the role-guidance hint that tells the agent
which values to suggest when nudging users to fill in project settings
currently lists `archetype: new-dwelling, renovation, ...`. Replace with the
taxonomy values (building class / work type) since that's what's actually
settable now.

### Frontend

- `ProjectControlBoard.tsx`: delete the Archetype `OverlaySelectField` and
  its `archetype` state from `ProjectProfilePanel`; grid goes from 3 columns
  (Role/Archetype/State) to 2 (Role/State); `saveProfile()` stops sending
  `archetype`. Update both "Set role, archetype, and state..." hint strings
  to reference class/work type instead.
- `CreateProjectPanel.tsx`: delete `deriveArchetype()` and its call site —
  nothing computes or sends `archetype` on create anymore.
- `project-overlays.ts`: drop the now-unused `projectArchetypeOptions`.
- `lib/types/project.ts`: drop `archetype` from `CreateProjectInput` and
  `UpdateProjectInput` (still present on `ProjectSummary`/`ProjectDetail` for
  reading legacy rows).

### Tests

- Rewrite `backend/tests/sitewise/test_gate.py` for the dual-path rule:
  taxonomy-complete -> ready; legacy-archetype-only -> ready; neither ->
  `missing` on `building_class` and `work_type`.
- Extend `backend/tests/test_project_taxonomy_api.py`'s overlay PATCH test
  (currently uncommitted, sets `archetype` directly) with a case proving the
  gate goes ready from `building_class`+`work_type` alone with no
  `archetype` sent.
- Add an MCP test exercising `list_platform_knowledge` for a taxonomy-only
  project (no archetype) to lock in the crash fix.
- Update `ProjectControlBoard.test.tsx`'s expected `updateProject` payload
  to drop `archetype`.

## Definition of done

`uv run pytest` (backend) and `npm run test` (frontend) green; manual smoke:
create a project via Class+Work type only (no archetype anywhere), confirm
Project Profile shows no Archetype field, confirm the overlay gate goes
"Ready" from Class+Work type+Role+State, confirm Create PMP runs and
`list_platform_knowledge` (via chat) doesn't error for that project. Confirm
the existing seeded default project (archetype-only, e.g.
`small-commercial`) still gates ready with zero changes.
