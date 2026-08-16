# Program Gantt Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a left-nav Program page that is a simple interactive Gantt, and optionally render that same Gantt as a read-only fitted figure in the PMP.

**Architecture:** Mirror Cost Plan. Typed `programme_versions` + `programme_activities` are the source of truth. The LLM proposes stages, activities, and durations; Python owns start/finish, finish-to-start links, and stage rollups. The Program page is the only editor. The PMP shows a non-editable figure at the current Program scale, squeezed to the page, behind a toolbar toggle.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, existing Pi MCP tools, React + TypeScript, custom SVG Gantt (no new npm Gantt library). Date math uses `datetime.date` / native `Date`.

---

## Locked decisions

| Topic | Choice |
|---|---|
| Nav label | **Program** (user-facing). Domain copy in PMP stays **Programme**. |
| Tile id | `program`, inserted after Cost Plan. |
| Folder | Existing `06-programme`. Remap workspace slug `programme` from the unimplemented `delivery` tile to `program`. |
| Source of truth | Typed programme tables. No markdown programme draft. No Excel/MPP in v1. |
| Chart library | Custom SVG. Do not add Frappe, Bryntum, or DHTMLX. Theme tokens must match Cost Plan (`cost-plan-surface` / `--sw-void`, `--sw-edge`, `--sw-beam`). |
| Default seed | Three stages: Planning (90d), Procurement (60d), Delivery (365d). Planning starts today unless the project has a known start. Procurement and Delivery are finish-to-start linked. No child activities until the user or agent adds them. |
| Activity kinds | `stage` (summary bar), `activity` (child bar), `milestone` (zero-duration diamond). |
| Links | Optional single finish-to-start predecessor + integer lag days. No SS/FF, no calendars, no critical path, no baseline, no % complete, no resources. |
| Floating vs linked | No predecessor = floating. Predecessor set = linked. Dragging a linked bar converts it to floating (clears predecessor). Duration resize keeps the link. |
| Scale | `week` \| `month` \| `quarter`. Stored on the programme version. Program page and PMP figure use the same value. |
| Date basis | Calendar days. Python computes `finish = start + duration_days` (milestone duration is 0; finish = start). |
| Stage rollup | Stage start = min child start; stage finish = max child finish. A stage with no children keeps its own start/duration. |
| Agent | No durable `create_programme` workflow in v1. Agent reads `get_programme`, writes `apply_programme_operations` (max 80 ops). First visit or first write calls `ensure_programme` to seed the three stages. |
| Activity library | Do not invent a new catalogue. Agent consults `data/seed/program-scheduling-guide.md` and the PMP sub-milestone table. Cap ~80 activities. |
| PMP relationship | PMP keeps the high-level milestone table. It does not become a second editor. Named key dates later sync from Program milestones; that sync is a follow-up, not v1. |
| PMP figure | Read-only. Same bars, colours, and stored scale as Program. Fitted to the PMP column (no horizontal scroll). Not draggable. Clicking it can open Program. |
| PMP toggle | Gantt icon on the PMP chrome (same family as Hide changes). Shown only when a programme exists. Default **on**. Persisted as `pmp_embed_visible` on the programme version. Hidden = omitted from the PMP view and from copy/export. |
| Figure injection | Frontend inserts the figure immediately under the Programme heading. Do not bake a PNG into markdown. For copy/export, `GET .../programme/figure.svg` returns the same fitted SVG. |
| Capability | Same profile gate as PMP: `building_class`, `work_type`, `state`. Not NSW-only. Not cost-plan coverage. |
| Out of scope | Critical path, baselines, working calendars, holidays, lookaheads, delay/EOT, Excel/MPP, resource levelling, SS/FF, durable generation workflow, writing dates back into the PMP milestone table. |

---

## Data shape

`programme_versions`

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `project_id` | uuid | FK projects, cascade |
| `version` | int | Per-project, unique. Optimistic concurrency. |
| `created_by_user_id` | uuid | FK users |
| `status` | `proposed` \| `accepted` \| `superseded` | Latest non-superseded is current |
| `view_scale` | `week` \| `month` \| `quarter` | Default `month` |
| `pmp_embed_visible` | bool | Default `true` |
| `created_at` | timestamptz | |

`programme_activities`

| Field | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `programme_version_id` | uuid | FK, cascade |
| `activity_key` | str | Stable slug, unique per version (`planning`, `da-lodgement`) |
| `kind` | `stage` \| `activity` \| `milestone` | |
| `parent_key` | str \| null | Stage key for activities/milestones. Null for stages. |
| `name` | str | |
| `display_order` | int | |
| `start_date` | date | |
| `duration_days` | int | `>= 0`. Milestone must be 0. |
| `finish_date` | date | Stored computed value |
| `predecessor_key` | str \| null | Same-version activity_key |
| `lag_days` | int | Default 0 |
| `assumption` | bool | Default true for seeded/agent rows |
| `notes` | text | Default empty |

Operations (same verb set as Cost Plan):

```text
ADD | UPDATE | DELETE | MOVE
target_type: stage | activity | milestone
```

Plus two programme-level updates on the version, not as activity ops:

- `view_scale`
- `pmp_embed_visible`

Copy-on-write: each successful mutation inserts a new version, marks the previous `superseded`, and returns the new state. `expected_base_version` must match the current version or the API returns 409.

---

## Task 1: Schedule math

**Files:**
- Create: `backend/app/programme/schedule.py`
- Test: `backend/tests/programme/test_schedule.py`

**Step 1: Write the failing tests**

```python
from datetime import date

from app.programme.schedule import (
    ActivityDraft,
    apply_link_move,
    rollup_stages,
    schedule_activities,
)


def test_finish_is_start_plus_duration_days() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            )
        ]
    )
    assert rows[0].finish_date == date(2026, 11, 14)


def test_milestone_finish_equals_start() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="da",
                kind="milestone",
                start_date=date(2026, 9, 1),
                duration_days=0,
            )
        ]
    )
    assert rows[0].finish_date == date(2026, 9, 1)


def test_linked_successor_starts_at_predecessor_finish_plus_lag() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            ),
            ActivityDraft(
                activity_key="procurement",
                kind="stage",
                start_date=date(2026, 1, 1),
                duration_days=60,
                predecessor_key="planning",
                lag_days=0,
            ),
        ]
    )
    by_key = {row.activity_key: row for row in rows}
    assert by_key["procurement"].start_date == date(2026, 11, 14)


def test_floating_activity_keeps_its_start() -> None:
    rows = schedule_activities(
        [
            ActivityDraft(
                activity_key="planning",
                kind="stage",
                start_date=date(2026, 8, 16),
                duration_days=90,
            ),
            ActivityDraft(
                activity_key="long-lead",
                kind="activity",
                parent_key="planning",
                start_date=date(2026, 7, 1),
                duration_days=30,
            ),
        ]
    )
    assert rows[1].start_date == date(2026, 7, 1)


def test_drag_clears_predecessor() -> None:
    moved = apply_link_move(
        ActivityDraft(
            activity_key="procurement",
            kind="stage",
            start_date=date(2026, 11, 14),
            duration_days=60,
            predecessor_key="planning",
        ),
        new_start=date(2026, 12, 1),
    )
    assert moved.predecessor_key is None
    assert moved.start_date == date(2026, 12, 1)


def test_stage_rollup_uses_children() -> None:
    rows = rollup_stages(
        schedule_activities(
            [
                ActivityDraft(
                    activity_key="delivery",
                    kind="stage",
                    start_date=date(2026, 1, 1),
                    duration_days=10,
                ),
                ActivityDraft(
                    activity_key="slab",
                    kind="activity",
                    parent_key="delivery",
                    start_date=date(2026, 2, 1),
                    duration_days=14,
                ),
                ActivityDraft(
                    activity_key="frame",
                    kind="activity",
                    parent_key="delivery",
                    start_date=date(2026, 2, 20),
                    duration_days=21,
                ),
            ]
        )
    )
    delivery = next(row for row in rows if row.activity_key == "delivery")
    assert delivery.start_date == date(2026, 2, 1)
    assert delivery.finish_date == date(2026, 3, 13)
```

Also test: cycle detection (`planning → procurement → planning` raises `ValueError`), missing predecessor raises, negative duration raises, milestone with duration > 0 raises.

**Step 2: Run to verify fail**

```bash
cd backend
uv run pytest tests/programme/test_schedule.py -v
```

Expected: FAIL — `app.programme` does not exist.

**Step 3: Implement**

`backend/app/programme/__init__.py` empty. `schedule.py` is a dataclass + three functions. Use `datetime.timedelta`. Resolve links in topological order. Do not use a graph library.

**Step 4: Re-run tests — expect PASS**

**Step 5: Commit** `feat: add programme schedule math`

---

## Task 2: Schemas and operations

**Files:**
- Create: `backend/app/programme/schemas.py`
- Test: `backend/tests/programme/test_schemas.py`

**Step 1: Write failing tests** for `ProgrammeActivityInput`, `ProgrammeOperation`, `ProgrammeState`.

Rules to encode:

- `extra="forbid"`
- `ADD` / `UPDATE` require `values`
- non-`ADD` requires `target_id` (the `activity_key`)
- `MOVE` requires `reference_id` + `placement`
- milestone `duration_days` must be 0
- `kind="stage"` forbids `parent_key`
- `kind` in `{activity, milestone}` requires `parent_key`
- max 80 operations per request

**Step 2: Run to verify fail, then implement to match Cost Plan’s `CostPlanOperation` shape in `backend/app/cost_plan/schemas.py:155`.**

**Step 3: Commit** `feat: add programme operation schemas`

---

## Task 3: Models and migration

**Files:**
- Create: `backend/app/programme/models.py`
- Modify: `backend/app/database/models.py` (import + `__all__`)
- Create: `backend/alembic/versions/047_programme.py`
- Test: `backend/tests/programme/test_models.py` (constraint constants / table names only; no live DB)

**Step 1: Write a unit test that imports the models and asserts table names, check constraint names, and the unique `(project_id, version)` / `(programme_version_id, activity_key)` pairs.**

**Step 2: Implement models** following `backend/app/cost_plan/models.py`. FK `programme_activities.programme_version_id` → `programme_versions.id` ON DELETE CASCADE. FK `programme_versions.project_id` → `projects.id` ON DELETE CASCADE.

**Step 3: Alembic 047**

```text
Revision ID: 047_programme
Revises: 046_workflow_run_queue_scope
```

Create both tables, checks, uniques, and `ix_programme_versions_project_status`.

**Step 4: Commit** `feat: add programme tables`

Do not run `alembic upgrade` against production from this plan. Local/dev upgrade is `uv run alembic upgrade head` from `backend/`.

---

## Task 4: Service — ensure, read, apply

**Files:**
- Create: `backend/app/programme/service.py`
- Create: `backend/app/programme/seed.py`
- Test: `backend/tests/programme/test_service.py`

Use the same in-memory session style as `backend/tests/cost_plan/test_typed_cost_plan.py`. Do not hit a live database.

**Behaviour**

- `get_programme(session, project_id)` → current version or raise `ProgrammeNotFound`
- `ensure_programme(...)` → current version, or insert v1 with the three default stages from `seed.py`
- `apply_programme_operations(...)` → copy-on-write new version, run `schedule_activities` + `rollup_stages`, 409 on stale `expected_base_version`
- `set_programme_view(...)` → copy-on-write `view_scale` and/or `pmp_embed_visible`
- Deleting a stage deletes its children
- Deleting a predecessor clears `predecessor_key` on dependents (they become floating, dates stay)
- Default seed dates: `date.today()` for Planning; linked successors computed by schedule math

**Step 1: Failing tests for ensure, stale version, add activity under Delivery, drag-clears-link, delete stage cascade, scale update.**

**Step 2: Implement service.**

**Step 3: Commit** `feat: add programme service`

---

## Task 5: REST API

**Files:**
- Modify: `backend/app/schemas/projects.py` — add `ApplyProgrammeOperationsRequest`, `SetProgrammeViewRequest`
- Modify: `backend/app/api/projects.py` — three routes next to the cost-plan block at `:2940`
- Test: `backend/tests/programme/test_programme_api.py` (handler-level, mock session like other project API unit tests)

Routes:

```text
GET  /projects/{project_id}/programme/state
POST /projects/{project_id}/programme/ensure
POST /projects/{project_id}/programme/operations
PATCH /projects/{project_id}/programme/view
GET  /projects/{project_id}/programme/figure.svg
```

`GET state` returns 404 until ensure has run. The Program page calls ensure on first open so the empty project is not a dead end.

`figure.svg` is implemented in Task 11; in this task return 501 or skip the route until then.

Auth: same `_require_project_owner` + `require_active_entitlement` on writes as cost-plan operations.

**Commit** `feat: add programme HTTP API`

---

## Task 6: MCP tools and agent instructions

**Files:**
- Modify: `backend/app/mcp_bridge/server.py` — add `get_programme`, `ensure_programme`, `apply_programme_operations`, `set_programme_view`
- Modify: `backend/app/agent/pi_process.py` — append those four names to `PI_MCP_DIRECT_TOOLS`
- Modify: `backend/app/agent/workspace_instructions.py` — programme section next to the cost-plan tools
- Modify: `backend/app/agent/turn_context.py` — same read-then-write rule as cost plan
- Test: `backend/tests/mcp_bridge/test_ai_operation_tools.py` (follow the cost-plan operation tests)
- Test: `backend/tests/agent/test_workspace_instructions.py`
- Test: `backend/tests/agent/test_pi_process.py` (allowlist contains the new names)

**Agent rules to write into workspace instructions**

1. For factual project dates, use project evidence tools first.
2. For construction sequencing, read `program-scheduling-guide.md` via platform knowledge. Label it guidance, not evidence.
3. Call `get_programme` (or `ensure_programme` if missing) before `apply_programme_operations`.
4. Propose names, stage grouping, durations, and which rows are linked. Do not compute calendar finishes in prose and then write them — send `start_date` + `duration_days` + optional `predecessor_key` and let Python schedule.
5. Default to the three stages. If the user asks for N stages / M activities, stay under 80 activities and 6 stages.
6. After writing, tell the user the Program page now has the Gantt. Do not dump a markdown Gantt into chat.
7. Duration phrases (“about three months”, “two years”) become `duration_days` (90 / 730). Mark `assumption=true` unless a document date was cited.

**Commit** `feat: expose programme tools to the agent`

---

## Task 7: Frontend types and API client

**Files:**
- Create: `frontend/src/lib/programme.ts`
- Create: `frontend/src/lib/programme.test.ts`
- Modify: `frontend/src/lib/api.ts` — `getProgrammeState`, `ensureProgramme`, `applyProgrammeOperations`, `setProgrammeView`

Types mirror the Python schemas. Include a small helper `isLinked(activity)` and `defaultScale`.

**Commit** `feat: add programme client types`

---

## Task 8: Program Gantt component

**Files:**
- Create: `frontend/src/components/project/ProgramGantt.tsx`
- Create: `frontend/src/components/project/ProgramGantt.test.tsx`
- Modify: `frontend/src/index.css` — `.program-gantt-surface` copied from `.cost-plan-surface` (do not invent a new palette)

**Component API**

```ts
type ProgramGanttProps = {
  state: ProgrammeState;
  mode: "edit" | "figure";
  onOperate?: (operations: ProgrammeOperation[]) => void;
  onScaleChange?: (scale: ProgrammeScale) => void;
};
```

**Edit mode (Program page)**

- Left: compact name column (stage names bold, children indented)
- Right: SVG time axis at `state.view_scale`
- Today line
- Stage bars, activity bars, milestone diamonds
- Optional FS arrows when `predecessor_key` is set
- Drag bar → `UPDATE` start + clear predecessor
- Drag right edge → `UPDATE` duration_days
- Click row → thin inspector: name, duration, start, linked/floating, delete
- Header: scale segmented control (Week / Month / Quarter), Add stage, Add activity
- Empty children: stages still render so the page is never a blank void

**Figure mode (PMP)**

- `pointer-events: none` on bars (the wrapping figure may still be a link/button to Program)
- No inspector, no add buttons, no scale control
- Width 100% of the PMP column; time axis is scaled to `min(start)…max(finish)` so the whole programme fits. No horizontal scroll.
- Same colours and stored scale as edit mode

**Tests (vitest)**

- Renders three default stage names
- Edit mode has scale buttons; figure mode does not
- Figure mode has no drag handles (`data-interactive` absent)
- Changing scale calls `onScaleChange`

Keep the first version visually quiet: one bar colour per kind, beam highlight on select, muted arrows. No grid chrome beyond light vertical week/month ticks.

**Commit** `feat: add Program Gantt component`

---

## Task 9: Left nav and Program workbench

**Files:**
- Modify: `frontend/src/components/project/workflow/workflowTiles.ts` — insert `{ id: "program", label: "Program", folder: "06-programme", icon: GanttChart }` after Cost Plan
- Modify: `frontend/src/components/project/workflow/workflowTiles.test.ts` — expected id order includes `program`
- Modify: `frontend/src/components/project/workflow/workflowRouting.ts` — `programme: "program"`, add `program` to `IMPLEMENTED_TILES`
- Modify: `frontend/src/components/project/ProjectControlBoard.tsx` — `isProgram` branch: no Create/Refresh buttons; just `ProgramGantt` after `ensureProgramme`
- Modify: `frontend/src/pages/ProjectCockpitPage.tsx` — treat `program` like `cost-plan` for workbench selection (no draft dependency)
- Modify: `frontend/src/pages/CockpitPreviewPage.tsx` — preview tile if the preview lists lifecycle tiles
- Test: `frontend/src/components/project/ProjectControlBoard.test.tsx`
- Test: `frontend/src/pages/ProjectCockpitPage.test.tsx` as needed

Program workbench empty/error states:

- Overlay not ready → same `OverlayGateNotice` as Cost Plan
- Capability not supported → `CapabilityGateNotice`
- Ensure/load failure → short error, retry

Do not add Create program / Refresh program buttons. The page *is* the programme. Chat creates detail.

**Commit** `feat: add Program nav and workbench`

---

## Task 10: PMP read-only figure and toggle

**Files:**
- Modify: `frontend/src/components/project/DraftReviewPanel.tsx`
- Modify: `frontend/src/components/project/MarkdownContent.tsx` if the figure is injected as a markdown visitor; prefer a DraftReviewPanel wrapper so MarkdownContent stays document-generic
- Modify: `frontend/src/components/project/DraftReviewPanel.test.tsx`
- Modify: `frontend/src/components/project/MarkdownContent.test.tsx` only if the visitor lives there

**Behaviour**

1. When `isPmpDraft(workflowType)` and `projectId` is set, fetch `getProgrammeState`. 404 → no icon, no figure.
2. If a programme exists, show a ghost icon button in the PMP header row (next to existing chrome, `print:hidden`):
   - `GanttChart` + `aria-label="Show programme in PMP"` / `"Hide programme from PMP"`
   - Pressed state follows `pmp_embed_visible`
3. Toggle calls `setProgrammeView({ pmp_embed_visible })`.
4. When visible, render `<ProgramGantt mode="figure" />` immediately under the first `h2` whose text is `Programme` or `Programme of services` or `Programme and staging regime`.
5. The figure is a button/link: “Open Program” / click navigates to the `program` tile (`onSelectWorkflow("program")` or `?workflow=program`).
6. Bars are not editable in this view.

**Tests**

- No programme → no gantt icon
- Programme + visible → figure present under Programme heading
- Click icon → `setProgrammeView` called with `pmp_embed_visible: false` and figure leaves the document
- Figure has no duration drag handle
- Advisory PMP heading `Programme of services` still hosts the figure

**Commit** `feat: embed read-only Gantt in the PMP`

---

## Task 11: Fitted SVG for copy/export

**Files:**
- Create: `backend/app/programme/figure.py`
- Test: `backend/tests/programme/test_figure.py`
- Wire `GET /projects/{project_id}/programme/figure.svg` from Task 5
- Modify PMP copy path in `DraftReviewPanel` / `CopyContentButton` so that when `pmp_embed_visible` the copied markdown inserts the SVG (or a relative image reference) under the Programme heading

**SVG rules**

- Width 720, height `40 + 28 * row_count`
- Same scale as `view_scale`
- No interactivity
- Dark tokens as hex matching `--sw-void` / `--sw-beam` / `--sw-edge` so the figure matches the PMP sheet
- Escape activity names

This is the “image in the document” the PMP needs when copied or printed. The in-app figure from Task 10 is the live view; this endpoint is the static snapshot at the same scale.

**Commit** `feat: render programme SVG for PMP export`

---

## Task 12: Delete, capabilities, and agent chat command

**Files:**
- Modify: `backend/app/projects/project_delete.py` — delete `ProgrammeVersion` before `CostPlanVersion` if it also RESTRICTs anything; with ON DELETE CASCADE from projects this may be unnecessary, but add it if the version row RESTRICTs users/drafts. Follow the existing “delete restrictors first” comment.
- Modify: `backend/tests/projects/test_project_delete.py`
- Modify: `backend/app/projects/workflow_capabilities.py` — `EDIT_PROGRAMME = "edit_programme"` using `_required_profile_capability` and `_PROJECT_PLAN_FIELDS`
- Modify: `backend/tests/projects/test_workflow_capabilities.py`
- Modify: `frontend/src/lib/workflow-chat-commands.ts` — `"create_programme"` → `"Create a program"`
- Modify: `frontend/src/lib/workflow-chat-commands.test.ts`
- Modify: `backend/app/agent/turn_context.py` if capability text is listed there

**Commit** `feat: wire programme capability, delete, and chat command`

---

## Implementation notes

**Determinism.** The model may choose “Delivery is two years” and “link Procurement to Planning”. It must not invent “Procurement therefore starts 14 November 2026” as a written fact. Python produces that date.

**PMP is not a second Gantt.** If a user tries to drag the PMP figure, nothing happens. The icon is the only PMP control. Edits happen on Program.

**Do not start a `create_programme` durable workflow.** Cost Plan needs one because of evidence sweep + workbook rebuild. Program v1 is a structured list of bars. The live agent turn is enough.

**Do not add a Gantt npm dependency.** A 20–50 row CM programme is the product surface; theme control matters more than an enterprise scheduler.

**Seed, don’t invent.** `data/seed/program-scheduling-guide.md` already has the house-building milestone spine (design lock, DA, CC, site start, slab, frame, lockup, fixing, PC, OC, DLP) and cycle-time ranges. The PMP sub-milestone table in `backend/app/sitewise/pmp_greenfield_brief.py` is the short list. Use those when the user says “create a program” or “about 40 activities”.

**Suggested first agent prompt after ship:** “Create a program. Use the three default stages and add about 20 house-building activities from the scheduling guide. Link only the gates that must be sequential.”

---

## Verification

Backend, from `backend/`:

```bash
uv run pytest tests/programme tests/mcp_bridge/test_ai_operation_tools.py tests/agent/test_workspace_instructions.py tests/agent/test_pi_process.py tests/projects/test_project_delete.py tests/projects/test_workflow_capabilities.py -q
uv run ruff check app/programme tests/programme
```

Frontend, from `frontend/`:

```bash
pnpm typecheck
pnpm lint
pnpm exec vitest run src/lib/programme.test.ts src/components/project/ProgramGantt.test.tsx src/components/project/workflow/workflowTiles.test.ts src/components/project/DraftReviewPanel.test.tsx
```

Manual:

1. Open a project → Program. Three stages appear. Drag Delivery; it detaches from Procurement.
2. Chat: “Create a program with about 20 activities.” Bars appear; PMP is unchanged except the figure.
3. Open Project Plan. Gantt icon is on. Figure sits under Programme, fitted, not draggable.
4. Turn the icon off. Figure disappears. Turn it on. Same scale as Program (Month unless changed).
5. On Program, switch to Quarter. PMP figure uses Quarter after reload.
6. Click the PMP figure → Program page.
