# RFP Quality Overhaul & Live Consultant-Status Tracking — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the consultant Request-for-Fee-Proposal (RFP) workflow up to the
same evidence-grounded, numbered-citation quality as Create PMP, and add a live,
clickable consultant-engagement status control inside the PMP's Consultants
section that updates the document immediately, without a full PMP regeneration.

**Architecture:** Reuse the PMP hybrid-compiler pattern (deterministic scaffold +
bounded LLM narrative pass) for RFP generation, reusing the existing generic
`[n]` citation module as-is. Reuse the existing `ProjectDecision` restamp-on-write
architecture (fenced-JSON-block-in-markdown → live PUT → immediate re-render,
no full workflow re-run) as the template for a new `consultant_procurement_status`
tracker.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / Alembic / `pydantic_ai`
(backend), React / `react-markdown` / TypeScript (frontend), pytest + Vitest.

**Order:** Part 1 (RFP quality) must ship before Part 2 (status tracker), because
Part 2's automatic "RFP issued" transition needs Part 1's real RFP drafts to
react to. Within each part, do tasks in numeric order — each depends on the one
before it.

## Implementation status (2026-07-22)

- [x] Task 1.1 â€” shared procurement render seam accepts asynchronous renderers.
- [x] Task 2.1 â€” town planner, heritage, fire-engineer, and acoustic-consultant
  profiles plus RFP fixtures/tests.
- [x] Task 3.1 â€” deterministic RFP scaffold and stable numbered citation key.
- [x] Task 4.1 â€” bounded RFP narrative agent and citation-labelled evidence prompt.
- [x] Task 5.1 â€” narrative validation and retry loop.
- [x] Tasks 6.1â€“8.1 â€” workflow integration, upstream error handling, and
  end-to-end RFP fixtures.
- [ ] Part 2 - live consultant-status tracking.

### Post-Part-1 follow-up fixes (found during review, 2026-07-22)

Two bugs surfaced while reviewing a live Walsh Two RFP draft, both fixed and
regression-tested; neither was anticipated by the tasks above:

1. **Discipline-alias gap re-opened the generic-fallback hole Task 2.1 closed.**
   `DISCIPLINE_ALIASES` had no entry for "town planning" (only the canonical
   name "town planner" hit the new profile), so a discipline argument phrased
   as "Town planning" still fell through to `normalise_discipline()`'s generic
   fallback - spinning up a second, disconnected `consultant_procurement_town_planning_*`
   workflow lineage alongside the correct `consultant_procurement_town_planner_*`
   one (visible in Walsh Two's `02-consultant/` folder as duplicate v01/v02
   pairs). Fixed by adding `"town planning"`, `"town planning consultant"`, and
   `"planning consultant"` to `DISCIPLINE_ALIASES`
   (`backend/app/workflows/consultant_procurement.py`). Regression test:
   `test_town_planning_phrasings_alias_to_town_planner` in
   `backend/tests/workflows/test_consultant_procurement.py`. The stray
   `consultant_procurement_town_planning_*` drafts/files already created for
   Walsh Two are not cleaned up by this fix - they're pre-existing project data
   and need manual removal via the app.
2. **Workspace-tree self-heal was dead code.** `_ensure_pmp_workspace_file`,
   `_ensure_cost_plan_workspace_file`, and
   `_ensure_consultant_procurement_workspace_files`
   (`backend/app/api/projects.py`) exist specifically to re-sync a
   `draft_artifacts` row to real storage plus a `workspace_files` row when one
   is missing, but the calls to them were removed from both
   `get_project_cockpit_bootstrap` and `get_project_workspace_tree` in commit
   `939784e4` ("feat(artefacts): implement canonical stage 4 revisions") while
   the function bodies were left behind unused. Net effect: any draft whose
   workspace-file sync never completed (partial failure, legacy pre-sync data,
   etc.) shows up permanently in the document tree - because
   `_workspace_paths_for_tree` unions in the draft's `workspace_path` directly,
   regardless of whether a real file backs it - but can never be opened or
   downloaded, and can never repair itself. This is what "the file is listed
   in the document repo but doesn't actually exist" turned out to be. Fixed by
   restoring the three calls in both endpoints. The existing tests for these
   endpoints only patched the ensure-functions as no-op passthroughs and never
   asserted they were called, which is how the regression shipped unnoticed;
   added `assert_awaited_once()` checks on all three in
   `test_cockpit_bootstrap_includes_consultant_procurement_drafts`
   (`backend/tests/test_project_cockpit_bootstrap.py`) to close that hole.

---

## Background — why the town-planner RFP came out poor

Traced live: chat agent → `draft_consultant_procurement_artifact` MCP tool
(`backend/app/mcp_bridge/server.py:2320`) →
`backend/app/workflows/consultant_procurement.py` → shared engine
`backend/app/workflows/procurement_request.py`.

Three compounding root causes, confirmed by reading the code and a real fixture
(`backend/tests/workflows/fixtures/consultant_rfp_structural_v01.md`):

1. **No LLM in the RFP path at all.** `_render_markdown()`
   (`consultant_procurement.py:866`) is a pure deterministic f-string template —
   it lists retrieved document *paths* as bullets and appends one generic
   "Background" sentence; it never synthesises evidence into prose. Contrast
   with `create_pmp.py`, which runs a `pydantic_ai` `Agent` with a
   validate-then-retry loop.
2. **"Town planner" has no discipline profile.** `DISCIPLINE_PROFILES`
   (`consultant_procurement.py` lines 92–255) has 12 entries (architect,
   structural engineer, hydraulic engineer, geotechnical engineer, surveyor,
   BASIX/energy assessor, certifier, landscape architect, arborist, bushfire
   consultant, traffic consultant, civil/stormwater engineer). Town planner and
   heritage consultant are both missing, so requests for them fall through to
   the generic fallback in `normalise_discipline()` (lines 402–414) — three
   placeholder sentences with the discipline name spliced in. That's the
   thinnest output the system can produce, and it's what fired for Walsh Two.
3. **No numbered-citation scheme.** The RFP ends with one unstructured
   "Basis used: ..." sentence instead of the PMP's `[n]` tokens plus a closing
   `## Citation key` section (`backend/app/sitewise/pmp_citations.py` — already
   generic, reusable as-is, no PMP-specific code inside it).

Conclusion: the RFP generator is a template stub, not the evidence-grounded,
cited, validated pipeline the PMP has. Part 1 below fixes that.

How the Consultants section currently gets its Status column (needed for Part 2):
`pmp_renderer.py: _render_taxonomy_consultants` (line 1182) rebuilds the whole
Consultants table on every Create/Update PMP run, and Status/Citation come
*only* from filed evidence (`has_engagement_evidence` / `has_fee_proposal_evidence`
in `mobilisation_evidence.py` — an engagement letter or fee proposal document
must already be ingested). Issuing an RFP isn't tracked at all today, and there
is no manual override.

---

## Part 1 — RFP workflow redesign

### Task 1.1 — Allow async `render()` in the shared procurement engine

**Files:**
- Modify: `backend/app/workflows/procurement_request.py`

**Why:** `procurement_request.py`'s `draft_procurement_request()` is shared by
both `consultant_procurement.py` (RFP) and `contractor_procurement.py`
(head-contractor EOI/RFT). The RFP path needs to become LLM-driven; the EOI/RFT
path must stay deterministic and untouched (no new LLM cost, no behaviour
change).

**Step:** At the render call site (around line 200, `markdown =
document.render(...)`), change to:

```python
import inspect
...
rendered = document.render(
    project=project,
    target=target,
    project_evidence=project_evidence,
    platform_knowledge=platform_knowledge,
    forecast=forecast,
    assumptions=assumptions,
    missing_inputs=missing_inputs,
    max_pages=pages,
    instructions=instructions,
)
markdown = await rendered if inspect.isawaitable(rendered) else rendered
```

`ProcurementDocument.render()`'s abstract method signature is unchanged; only its
return type widens to `str | Awaitable[str]`. `ContractorEoiDocument.render` in
`contractor_procurement.py` stays a plain sync method — do not touch it.

**Verify:** existing `backend/tests/workflows/test_consultant_procurement*.py`
and any contractor-procurement tests pass unmodified after this change (it's a
no-op for sync renderers).

---

### Task 2.1 — Add missing discipline profiles

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py`
- Add: `backend/tests/workflows/fixtures/consultant_rfp_town_planner_v01.md`

**Step:** In `DISCIPLINE_PROFILES` (lines 92–255), add two entries following the
exact `_profile(...)` pattern already used (see the `structural engineer` entry
as the closest template):

```python
_normalise_key("town planner"): _profile(
    "Town planner",
    benchmark_terms=("town planning", "planning"),
    requested_services=(
        "Review the project brief, site constraints, zoning (LEP/DCP), and proposed works.",
        "Advise on permitted use, FSR, height, setbacks, and any merit-based variations required.",
        "Confirm the planning pathway (CDC/DA) and any State-level (SEPP) referral requirements.",
    ),
    deliverables=(
        "Planning report / statement of environmental effects fee proposal.",
        "Assumptions on council pre-lodgement meetings and authority response timeframes.",
        "Hourly rates for RFIs, design changes, and section 4.55 modifications.",
    ),
),
_normalise_key("heritage consultant"): _profile(
    "Heritage consultant",
    benchmark_terms=("heritage",),
    requested_services=(
        "Review heritage listing / conservation area status, existing fabric, and proposed works.",
        "Advise on heritage impact, sympathetic design responses, and the applicable approval pathway.",
        "Coordinate documentation with the design team and identify authority consultation needs.",
    ),
    deliverables=(
        "Heritage impact statement fee proposal.",
        "Assumptions on site access, archival recording, and photographic survey scope.",
        "Hourly rates for additional advice or authority responses.",
    ),
),
```

Also audit for other obvious gaps in the same pass (fire engineer, acoustic
consultant) and add them with the same pattern if it's a trivial add — don't
scope-creep beyond disciplines that are clearly missing.

**Verify:** a new test asserting `normalise_discipline("town planner")` and
`normalise_discipline("heritage consultant")` return the new profiles, not the
generic fallback. Add the fixture file mirroring the existing structural-engineer
fixture's shape (post Task 4/5, this fixture's *content* will need updating again
once citations land — track that in Task 8).

---

### Task 3.1 — Deterministic RFP scaffold module

**Files:**
- Add: `backend/app/sitewise/rfp_renderer.py`

**Why:** Mirrors `pmp_renderer.py`'s split between deterministic structure and
LLM-authored prose. Handles everything that doesn't need language-model
judgement: headers, lists sourced straight from `DisciplineProfile`, and the
citation index/key.

**Step:** Build a module with:

- `build_rfp_citation_index(project_evidence: list[dict]) -> CitationIndex` —
  wraps `app.sitewise.pmp_citations.build_citation_index`. Input shape is the
  same `dict[str, Any]` list already produced by
  `procurement_request.py: _retrieve_project_evidence` (`relative_path`,
  `filename`, etc. — see `_project_evidence_item`). No changes needed to
  `pmp_citations.py`; it's already generic (no PMP-specific naming inside it).
- `render_rfp_scaffold(*, project, target: DisciplineProfile, citation_index,
  forecast, max_pages) -> str` — renders: `# Request for Fee Proposal —
  {target.name}`, `## Project` block (reuse the field list already in
  `consultant_procurement.py: _render_markdown`'s `project_lines`), `##
  Requested services`, `## Required deliverables`, `## Programme / response
  date`, `## Fee response requirements` (including the forecast line — reuse
  `_forecast_for_discipline`'s output), `## Exclusions / assumptions`, `## Site
  visit / clarifications`, `## Submission instructions`, and a closing `##
  Citation key` section built from `format_citation_key_lines(citation_index)`.
  Leave two named placeholder markers in the output string:
  `{{BACKGROUND}}` (replaces today's one-sentence `_background()` output) and
  `{{INFORMATION_TO_REVIEW}}` (replaces today's bare-path bullet list from
  `_information_to_review()`).

**Verify:** unit test that the scaffold contains both placeholder markers exactly
once each, and that the Citation key section lists every unique document in
`project_evidence`, numbered ascending by path (same ordering guarantee
`build_citation_index` already provides and is tested for elsewhere).

---

### Task 4.1 — RFP narrative LLM module

**Files:**
- Add: `backend/app/workflows/rfp_narrative.py`
- Add: `backend/app/workflows/rfp_narrative_instructions.md` (prompt/instructions
  file, same role as `pmp_narrative_instructions.md`)

**Why:** A small, bounded LLM pass — not a full freeform agent — that only fills
the two narrative slots left by Task 3.1's scaffold, grounded in real evidence
snippets and citing them with the *same* `[n]` numbers as the scaffold's
Citation key.

**Step:** Model this file directly on `backend/app/workflows/pmp_narrative.py`'s
shape:

```python
class RfpNarrativeOutput(BaseModel):
    background: str = Field(min_length=1)
    information_to_review: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

rfp_narrative_agent = Agent(
    f"openai-chat:{settings.pmp_model}",  # reuse existing model config; do not add a new setting unless the model differs
    output_type=RfpNarrativeOutput,
    instructions=_load_instructions(),  # rfp_narrative_instructions.md
    defer_model_check=True,
)

async def run_rfp_narrative_model(
    *,
    project: Project,
    target: DisciplineProfile,
    project_evidence: list[dict],
    platform_knowledge: list[dict],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
) -> RfpNarrativeOutput:
    ...
```

The prompt must include, per evidence item, both its content snippet **and**
`citation_index.token_for(item["relative_path"])` so the model is told exactly
which `[n]` to use for which document — don't let the model invent its own
numbering. Write `rfp_narrative_instructions.md` telling the model: every
sentence referencing a specific project document must end with its `[n]` token;
if no evidence exists for a claim, don't cite anything (no fabricated
citations); keep Background to 2–4 sentences; `information_to_review` is a list
of one-line strings, each ending in its `[n]`.

**Verify:** unit test with a fake evidence list asserting the prompt text
contains each document's assigned `[n]` token next to its snippet.

---

### Task 5.1 — Validation + retry loop for the RFP narrative

**Files:**
- Add (or extend Task 4.1's module): `backend/app/sitewise/rfp_evidence_validation.py`
- Modify: `backend/app/workflows/consultant_procurement.py`

**Why:** Mirrors `create_pmp.py: validate_pmp_output` /
`pmp_evidence_validation.py: evidence_grounded_violations` — reject and retry
instead of silently persisting a bad draft.

**Step:** `validate_rfp_output(output: RfpNarrativeOutput, *, citation_index:
CitationIndex) -> None` raising `WorkflowValidationError` (import the one
already defined in `app.workflows.create_pmp` — don't redefine a duplicate
exception type) when:
- `background` is empty or contains no `[n]` token despite `project_evidence`
  being non-empty (a "no evidence, so no claims" case is fine — check via
  whether the model was given any evidence at all, mirroring
  `evidence_grounded_violations`'s approach of only enforcing citations when
  evidence exists).
- Any `[n]` used in `background` or `information_to_review` doesn't resolve
  against `citation_index` (parse `\[(\d+)\]` and check against
  `citation_index.documents` length).
- `information_to_review` is empty while `project_evidence` is non-empty.

In `consultant_procurement.py`, wrap the narrative call in a retry loop (≤3
attempts, same shape as `create_pmp.py: run_create_pmp_hybrid` lines ~973–1055):
on `WorkflowValidationError`, feed `str(exc)` back in as `validation_feedback`
and retry; on the 3rd failure, re-raise.

**Verify:** test that an out-of-range citation (e.g. `[99]` when only 3 documents
exist) is rejected and triggers a retry; test that 3 consecutive failures raise.

---

### Task 6.1 — Wire the async pipeline into `ConsultantDocument.render()`

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py`

**Step:** Change `ConsultantDocument.render(...)` (currently delegates to
`_render_markdown`, around line 482) to `async def`, orchestrating in order:

1. `citation_index = build_rfp_citation_index(project_evidence)` (Task 3.1)
2. `scaffold = render_rfp_scaffold(project=project, target=target,
   citation_index=citation_index, forecast=forecast, max_pages=max_pages)`
   (Task 3.1)
3. Narrative + validate/retry loop (Tasks 4.1/5.1) → `RfpNarrativeOutput`
4. Assemble: replace `{{BACKGROUND}}` with the narrative's `background`, and
   `{{INFORMATION_TO_REVIEW}}` with the bulleted `information_to_review` list,
   in the scaffold string.
5. Return the assembled markdown.

Once this path is proven (Task 8's tests pass), delete the now-dead
`_render_markdown`, `_background`, `_information_to_review`, and `_basis_footer`
functions rather than leaving them as unused dead code — check nothing else in
the module still calls them first (`_basis_footer` may still be referenced by
`_source_trace`; keep whatever is still load-bearing).

---

### Task 7.1 — Upstream LLM error handling in the MCP tool

**Files:**
- Modify: `backend/app/mcp_bridge/server.py`

**Why:** The tool wrapper `draft_consultant_procurement_artifact`
(`server.py:2320`) has zero LLM-failure handling today because the old path
never called an LLM. Now it does, and a raw `OpenAIError` / `UnexpectedModelBehavior`
should not leak as an unhandled exception through `ToolError`.

**Step:** Reuse `create_pmp.py`'s `_upstream_failure_message(exc, operation=...)`
/ `_upstream_failure_metadata(exc, model=...)` helpers (import them, or extract
to a shared location if that's cleaner — check whether `create_pmp.py` already
exports them or if they need a `from app.workflows.create_pmp import
_upstream_failure_message` — if leading-underscore privacy is a concern, move
both helpers to a small shared module, e.g. `app/workflows/_upstream_errors.py`,
and have both `create_pmp.py` and `consultant_procurement.py` import from there).
Catch `(ModelAPIError, UnexpectedModelBehavior, OpenAIError)` around the
`run_consultant_procurement_artifact(...)` call in the tool, and raise
`ToolError(_upstream_failure_message(exc, operation="draft the RFP"))`.

---

### Task 8.1 — Update tests and fixtures for the new RFP shape

**Files:**
- Modify: `backend/tests/workflows/test_consultant_procurement.py`
- Modify: `backend/tests/workflows/test_consultant_procurement_evidence.py`
- Modify: `backend/tests/workflows/fixtures/consultant_rfp_structural_v01.md`
  (and any sibling fixtures) to the new citation-bearing shape
- Confirm unmodified: any `test_contractor_procurement*.py` (proves Task 1.1
  didn't change the EOI/RFT path)

**Step:** Update fixtures/assertions to expect: a populated `Background` with at
least one `[n]` citation when evidence exists, a non-empty `## Citation key`
section, and `Information to review` lines each ending in a resolvable `[n]`.
Add a test that forces a validation failure (e.g. mock the narrative agent to
return an out-of-range citation once, then a valid one) and asserts the retry
recovers and the final draft is clean.

**Part 1 definition of done:** regenerating the Walsh Two town-planner RFP
produces `[n]` citations in Background/Information-to-review that resolve to a
closing Citation key, grounded in real evidence content (not just file paths),
at the same quality bar as the PMP.

---

## Part 2 — Live consultant-status control in the PMP

Direct precedent to copy — do not invent a new architecture. `ProjectDecision`
(`backend/app/database/project_decision.py`,
`backend/app/projects/decisions.py`) is already a live, per-item, user-settable
value embedded in PMP markdown as a ` ```pmp-decision ` fenced JSON block. The
frontend intercepts it in `frontend/src/components/project/MarkdownContent.tsx`'s
`pre` renderer and swaps in `DecisionControl`
(`frontend/src/components/project/DecisionControl.tsx`). A click calls `PUT
/projects/{id}/decisions/{id}` with optimistic concurrency
(`expected_revision`/`expected_set_revision`,
`backend/app/api/projects.py` lines 1831+), and the backend **restamps the
change directly into the current draft markdown** (`restamp_decisions`, called
from `_restamp_shared_decision_drafts`) and returns the updated draft — no PMP
regeneration. Build the consultant-status control as this pattern's sibling,
reusing as much of its shape as possible.

Confirmed decisions (from product sign-off, do not re-litigate):
- **4-stage lifecycle:** `not_started` → `rfp_issued` → `fee_received` →
  `engaged`.
- Ship right after Part 1, in the same overall effort.

### Task 9.1 — Data model

**Files:**
- Add: `backend/app/database/consultant_procurement_status.py`
- Add: `backend/alembic/versions/<next_number>_consultant_procurement_status.py`

**Step:** SQLAlchemy model mirroring `project_decision.py`'s shape:

```python
class ConsultantProcurementStatus(Base):
    __tablename__ = "consultant_procurement_status"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    discipline_slug: Mapped[str] = mapped_column(nullable=False)  # matches consultant_procurement.py's _slugify output
    status: Mapped[str] = mapped_column(nullable=False, default="not_started")
    firm: Mapped[str | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(nullable=True)
    revision: Mapped[int] = mapped_column(nullable=False, default=1)
    locked: Mapped[bool] = mapped_column(nullable=False, default=False)
    source: Mapped[str] = mapped_column(nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("project_id", "discipline_slug"),)
```

`status` values: `not_started`, `rfp_issued`, `fee_received`, `engaged` (use a
plain string column with an application-level enum/`Literal`, matching how
`ProjectDecision.selected` is a plain string, not a DB enum — check
`project_decision.py` for the exact column-typing convention used there and
match it).

Check the latest file in `backend/alembic/versions/` for the next migration
number before naming the new file.

---

### Task 9.2 — Service layer

**Files:**
- Add: `backend/app/projects/consultant_status.py`

**Step:** Mirror `backend/app/projects/decisions.py` function-for-function:

- `list_consultant_statuses(session, *, project_id) -> list[ConsultantProcurementStatus]`
- `get_consultant_status(session, *, project_id, discipline_slug)`
- `update_consultant_status(session, *, project_id, discipline_slug, status,
  firm=None, note=None, expected_revision, actor_source, lock=None) ->
  ConsultantProcurementStatus` — same revision-conflict pattern as
  `update_project_decision`: raise a new `ConsultantStatusRevisionConflict` (mirror
  `DecisionRevisionConflict`) if `expected_revision` doesn't match; bump
  `revision`; call `publish_project_event(...)` with
  `resource_type="consultant_procurement_status"` (mirror `_publish_change` in
  `decisions.py`).
- `bump_status_if_unlocked(session, *, project_id, discipline_slug, new_status,
  actor_source="system") -> None` — the automatic-transition helper. Must:
  - No-op if the row is `locked`.
  - No-op if the new status is *not* strictly later in the lifecycle order
    `["not_started", "rfp_issued", "fee_received", "engaged"]` than the current
    one (never downgrade).
  - Create the row (status defaults appropriately) if it doesn't exist yet.

**Verify:** unit tests for revision-conflict raising, lock semantics blocking
both user and system updates appropriately (user updates with `lock=True` should
still work even if currently locked by a previous user action — mirror
`update_project_decision`'s `if row.locked and actor_source != "user"` check
exactly), and `bump_status_if_unlocked` never downgrading or touching a locked
row.

---

### Task 9.3 — API routes

**Files:**
- Modify: `backend/app/api/projects.py`
- Modify: `backend/app/schemas/projects.py` (request/response models)

**Step:** Add near the existing decisions routes (~line 1733/1831):

- `GET /{project_id}/decisions` → sibling `GET /{project_id}/consultant-status`
  (mirror `get_project_decisions`, list all tracked disciplines for the
  project).
- `PUT /{project_id}/decisions/{decision_id}` → sibling `PUT
  /{project_id}/consultant-status/{discipline_slug}` (mirror
  `put_project_decision`): body `{status, firm?, note?, expected_revision,
  lock?}`; on success, call a new `restamp_consultant_status(markdown,
  discipline_slug, status_row) -> str` that:
  - Locates the Consultants table row for that discipline in the latest PMP
    draft's markdown (match by discipline display name — same lookup approach
    `_render_taxonomy_consultants` uses for its `seen` dedup set).
  - Rewrites only that row's Status (and Citation, if applicable) cell text.
  - Persists via `revise_workflow_artefact` exactly like
    `_restamp_shared_decision_drafts` does for decisions (see
    `backend/app/api/projects.py` around line 1792 for the pattern), and
    returns the updated draft in the response so the frontend can render it
    immediately without a refetch race.
  - Same revision-conflict → HTTP 409 mapping as `put_project_decision`.

**Verify:** integration test hitting the PUT route and asserting the returned
draft's markdown has the updated Status cell for that discipline, with the rest
of the document byte-identical apart from that cell.

---

### Task 9.4 — Wire automatic transitions

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py`
- Modify: `backend/app/sitewise/pmp_sweep.py` (or wherever
  `mobilisation_evidence.py`'s evidence checks run during a PMP sweep — confirm
  exact call site by reading `pmp_sweep.py`'s `sweep_current_pmp_corpus`)

**Step:**
- In `consultant_procurement.py`'s `draft_consultant_procurement_artifact(...)`
  workflow function, after the draft is successfully created/committed, call
  `bump_status_if_unlocked(session, project_id=project.id,
  discipline_slug=target.slug, new_status="rfp_issued")`.
- In the PMP sweep path, wherever `has_engagement_evidence(pack)` /
  `has_fee_proposal_evidence(pack)` are evaluated per discipline, call
  `bump_status_if_unlocked(..., new_status="fee_received")` or `"engaged"`
  accordingly (read `mobilisation_evidence.py` closely here — the pack today is
  built per-project, not per-discipline for the general consultant roster;
  confirm whether discipline-level attribution is already available or needs a
  small extension to `MobilisationEvidencePack`/`extract_mobilisation_evidence_pack`
  before this task can be completed faithfully. If discipline attribution isn't
  available yet, scope this specific sub-step down to the Architect-PM row only
  — which already has discipline-specific `has_engagement_evidence` — and file a
  follow-up for the taxonomy-driven consultant roster rows).

---

### Task 9.5 — Merge tracked status into the Consultants table renderer

**Files:**
- Modify: `backend/app/sitewise/pmp_renderer.py` (`_render_taxonomy_consultants`,
  line 1182)

**Step:** Accept an additional parameter (tracked status rows, keyed by
discipline slug) and use it as the Status/Citation source of truth when a
tracked row exists for that discipline, falling back to the current
evidence-only derivation (`has_engagement_evidence`/`has_fee_proposal_evidence`)
only when no tracked row exists yet. This keeps a fresh Create/Update PMP run
consistent with whatever the live table currently shows, instead of reverting
progress the user or the auto-transitions already recorded.

Also: append one fenced ` ```consultant-status ` block per discipline row
directly under the rendered table (see Task 10.1 for the frontend side of this
contract) so the interactive control has something to attach to.

---

### Task 10.1 — Frontend control

**Files:**
- Add: `frontend/src/components/project/ConsultantStatusControl.tsx`
- Add: `frontend/src/components/project/ConsultantStatusControl.test.tsx`
- Modify: `frontend/src/components/project/MarkdownContent.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types/project.ts`

**Step:**
- `types/project.ts`: add `ConsultantStatus` type (`discipline_slug`, `status`,
  `firm?`, `note?`, `revision`, `locked`).
- `api.ts`: add `getConsultantStatus(projectId, disciplineSlug)` and
  `putConsultantStatus(projectId, disciplineSlug, status, expectedRevision,
  opts?)`, mirroring `api.putDecision`'s shape exactly (same error handling via
  `ApiError`).
- `ConsultantStatusControl.tsx`: mirror `DecisionControl.tsx`'s structure
  (local optimistic state, `isSaving`, rollback-on-error) but render a 4-stage
  stepper/badge row (`Not started` / `RFP issued` / `Fee received` / `Engaged`)
  instead of arbitrary option buttons — clicking a later stage than current
  commits directly to it (no need to click through every intermediate stage).
  Reuse `parseEmbeddedDecision`'s JSON-parsing defensiveness pattern for a new
  `parseEmbeddedConsultantStatus(raw)` helper.
- `MarkdownContent.tsx`: in the `pre` renderer (~line 101), add a second
  recognised fenced language check alongside `language-pmp-decision` —
  `language-consultant-status` — parsing with the new helper and rendering
  `ConsultantStatusControl` instead of `DecisionControl`.

**Verify:** component test asserting a click on a later stage calls
`putConsultantStatus` with the right arguments and updates the badge
optimistically, and rolls back on a simulated 409.

---

### Task 11.1 — Backend + frontend tests for Part 2

**Files:**
- Add: `backend/tests/projects/test_consultant_status.py` (model directly on
  `backend/tests/projects/test_decisions.py`: revision conflicts, lock
  semantics, auto-transition never downgrades or overwrites a locked row)
- Covered above: `ConsultantStatusControl.test.tsx`,
  `MarkdownContent.test.tsx` additions for the new fenced-block interception

**Part 2 definition of done:** clicking a consultant's status in the rendered
PMP updates that row's Status cell immediately (no PMP regeneration), persists
with optimistic concurrency, survives the next Update PMP run without being
silently reset, and auto-advances (never downgrades) when an RFP is issued or
engagement/fee-proposal evidence is filed.

---

## Answering "on the fly vs. regenerate" (context for whoever reviews this)

Yes — on the fly, continuously, no PMP re-run required for the status click
itself, using the same restamp-on-write mechanism already proven for
`ProjectDecision`. The rest of the PMP (risk register, programme, narrative
prose) still only refreshes on the next Update PMP run since that content is
LLM-authored — that part is unavoidable — but procurement progress specifically
never goes stale between full runs, because both the manual click (Task 9.3)
and real filed evidence (Task 9.4) keep the same tracked table current.

---

## Final verification (run after all tasks)

- `pytest backend/tests/workflows/test_consultant_procurement*.py
  backend/tests/workflows/test_contractor_procurement*.py
  backend/tests/projects/test_consultant_status.py
  backend/tests/projects/test_decisions.py`
- Frontend: `ConsultantStatusControl.test.tsx`, `DecisionControl.test.tsx`,
  `MarkdownContent.test.tsx`.
- Manual, end-to-end on Walsh Two (use the `verify` skill's dev-stack recipe):
  regenerate the town-planner RFP via chat and confirm `[n]` citations resolve
  to a Citation key with real project-specific prose; open the PMP, click
  through the 4 consultant-status stages for a discipline, and confirm the
  Consultants table cell updates live without a full PMP regeneration.
