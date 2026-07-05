# PMP 2.0 — Phase 5: Interactive PMP (Objective 1)

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13 (D1/D2/D8/D10/D11/D13 are the contract for this phase), test commands, recorded baseline test failures.
> **Depends on:** [Phase 1](01-phase-1-taxonomy-foundation.md). **Parallel-safe with:** Phases 2, 3, 4.

**Outcome:** PMP renders as an interactive document: agent-proposed selections are toggleable widgets whose overrides persist and survive regeneration; sections are editable in place.

## Task 5.1: Decision block format + parser

**Files:**
- Create: `backend/app/sitewise/pmp_decisions.py`
- Test: `backend/tests/sitewise/test_pmp_decisions.py`

Canonical embedded form (inside `content_markdown`):

````markdown
```pmp-decision
{
  "id": "procurement-route",
  "section": "Procurement posture",
  "label": "Procurement route",
  "options": [
    {"value": "traditional", "label": "Traditional (Lump Sum)"},
    {"value": "design_construct", "label": "Design & Construct"}
  ],
  "selected": "traditional",
  "source": "agent",
  "rationale": "Documented single-stage design suits lump sum."
}
```
````

API of the module (all deterministic, all tested):

```python
def extract_decisions(markdown: str) -> list[PmpDecision]: ...
def decision_violations(markdown: str) -> list[str]:
    """Malformed JSON, duplicate ids, selected not in options, missing keys."""
def restamp_decisions(markdown: str, locked: dict[str, str]) -> str:
    """Rewrite each block whose id is in `locked`: set selected + source='user'.
    Byte-stable outside the fenced blocks."""
def missing_locked_decisions(markdown: str, locked_ids: set[str]) -> list[str]: ...
def render_decisions_static(markdown: str) -> str:
    """Replace each block with '**{label}:** {selected label}' — for export/accept."""
```

Tests: round-trip stability, restamp preserves surrounding markdown byte-for-byte, malformed block reported not crashed, `sanitize_evidence_grounded_markdown` leaves fenced blocks intact (add that regression test against the real sanitizer).

## Task 5.2: `project_decisions` table

**Files:**
- Create: `backend/alembic/versions/019_project_decisions.py` (next free number)
- Create: `backend/app/database/project_decision.py` + `backend/app/database/project_decisions.py` (accessors, matching the `activity_event`/`activity_events` file pattern)
- Test: `backend/tests/database/test_project_decisions.py`

Columns: `id` UUID PK, `project_id` FK cascade, `decision_id` String(128), `section` String(256), `label` String(256), `options` JSONB, `selected` String(128), `source` String(16) (`agent`|`user`), `workflow_type` String(128) default `create_pmp`, timestamps; unique `(project_id, decision_id)`; index on project_id. Accessors: `upsert_decision`, `list_decisions(project_id)`, `locked_selections(project_id) -> dict[str, str]` (source=user only).

## Task 5.3: Generation emits + preserves decisions

**Files:**
- Modify: `backend/app/workflows/create_pmp_instructions.md` — new section: emit a `pmp-decision` block wherever the draft chooses among taxonomy-defined options (procurement route, contract form, approvals pathway (DA vs CDC), staging strategy, and any complexity dimension the evidence left open); ids kebab-case stable across versions; never invent options outside the provided taxonomy lists.
- Modify: `backend/app/workflows/create_pmp.py` — prompt includes available decision option sets (from taxonomy) and current `locked_selections`; post-generation: `decision_violations` folded into validation; `restamp_decisions(markdown, locked)` applied before persist; extracted decisions upserted (source=agent unless locked).
- Modify: `backend/app/workflows/update_pmp.py` — `missing_locked_decisions` added to `validate_update_pmp_output` (locked decisions are as protected as baseline headings); restamp + upsert as above.
- Tests: extend `backend/tests/workflows/test_create_pmp.py` (there's an existing test file — follow its fake-agent pattern) — locked user selection survives a regeneration that tried to flip it; validation error message when a locked block disappears.

## Task 5.4: Decision API

**Files:**
- Modify: `backend/app/api/projects.py`:
  - `GET /api/projects/{project_id}/decisions` → list
  - `PUT /api/projects/{project_id}/decisions/{decision_id}` body `{"selected": "design_construct"}` → validate against options, upsert row (`source="user"`), load latest draft for the decision's workflow_type, `restamp_decisions`, persist draft in place (same pattern as `patch_project_draft` — no version bump for a selection toggle), record activity event (`step="decision_override"`), return updated draft.
- Modify: `backend/app/schemas/projects.py` — `ProjectDecision` schema + request/response models.
- Test: `backend/tests/test_project_decisions_api.py` — toggle round-trip; invalid option → 422; draft markdown actually rewritten.

## Task 5.5: Frontend decision widgets

**Files:**
- Modify: `frontend/src/components/project/MarkdownContent.tsx` — custom `code` component: `language-pmp-decision` → parse JSON → render `<DecisionControl>`; parse failure → render the fence as-is (never crash the document).
- Create: `frontend/src/components/project/DecisionControl.tsx` — segmented control (≤4 options) or select (>4); provenance badge ("AI selection" muted / "Your selection" accent); rationale as caption; onChange → `api.putDecision` → optimistic update → `onDraftUpdated` with returned draft.
- Modify: `frontend/src/lib/api.ts`, `frontend/src/lib/types/project.ts`.
- Test: `frontend/src/components/project/DecisionControl.test.tsx` + a `MarkdownContent` test with an embedded block.

Conflict behaviour from D13: if a later refresh records that current corpus evidence disagrees with a user-locked selection, the widget keeps the user's value, shows an evidence-conflict state, and links/points to the relevant ActivityFeed run. Do not silently flip the value.

Read-only contexts (accepted drafts, exports): render via `render_decisions_static` markdown from the backend on accept — modify the accept endpoint to persist a static-rendered copy to the workspace file (check `upsert_workspace_file` call in accept flow) while `content_markdown` keeps live blocks.

## Task 5.6: Section-level inline editing

**Files:**
- Modify: `frontend/src/components/project/DraftReviewPanel.tsx` — per-`h2` "Edit section" affordance: textarea scoped to that section's markdown slice; save → splice into full markdown → existing `api.patchDraft`. Backend already validates on PATCH.
- Backend helper: `backend/app/sitewise/markdown_sections.py` already splits sections — implement the split in TS (`splitMarkdownSections(markdown): {heading, start, end}[]`) with tests — headings are the same `##` contract the backend enforces.
- Test: `DraftReviewPanel.test.tsx` — edit one section, other sections byte-identical.

## Task 5.7: Visual pass — "tables and visual cues"

**Files:** `frontend/src/components/project/MarkdownContent.tsx`, `frontend/src/index.css`.
- Style the evidence-map/status vocabulary: render `User provided`/`Grounded`/`Partial`/`Not evidenced`/`Assumption`/`Gap`/`Conflict` tokens inside table cells as coloured chips (string-match in the `td` renderer — the vocabulary is a tested backend contract).
- Sticky section nav (left rail of the PMP panel) built from `h2`s, chronological order preserved.
- Inline links from evidence-status rows/chips to the existing ActivityFeed/WorkflowTrace run where available. The PMP carries compact status; the trace carries the detailed sweep/seed-section log.
- Annexure affordance for linked/collapsed companion artifacts (full evidence map, risk/action/decision registers, approval/compliance register). The primary view remains printable inside the 2–4 page band.
- **A4 print stylesheet** (`@media print`): compact tables, decision blocks render as static "label: selected" text, sensible page-break rules (`break-inside: avoid` on tables), header/footer with project title + version. This stylesheet is the visual definition of the **2–4 page band** (D7) — print-preview a Phase 4 fixture draft and feed the result back into the `pmp_min_words`/`pmp_max_words` calibration (Phase 4 Task 4.3).
- No new markdown syntax; purely presentational. Component tests for chip mapping.

## Definition of done

Backend `uv run pytest tests/sitewise/test_pmp_decisions.py tests/database/test_project_decisions.py tests/test_project_decisions_api.py tests/workflows -v` green; `npm run test` green; manual smoke: generate PMP → flip a decision → regenerate (Update PMP) → user selection survives.
