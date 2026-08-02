# Peer Review — Procurement Requests (RFP / RFT / RFQ) Implementation Plan

**Reviewing:** [2026-08-02-procurement-requests-rfp-rft-rfq.md](./2026-08-02-procurement-requests-rfp-rft-rfq.md)
**Date:** 2026-08-02
**Status:** Review complete; revised staging not yet applied to the plan or the PRD.

> Code paths below are repo-root relative.

## Context

The plan extends Clerk's consultant-RFP capability to trade and main-works tendering: a long-form RFT for the main works contractor and a short-form RFQ for individual trades, reusing the procurement engine and PMP/cost-plan infrastructure rather than building parallel machinery.

The review brief was: keep it lean and low-code, don't over-engineer, drop the recipients/contacts schema (the user will send artefacts from their own Outlook), keep the RFQ genuinely short, and keep the new left-nav dashboard as light as the recently stripped-down Create PMP and Cost Plan panels.

**Verdict:** the architectural premise is correct and well-evidenced — but the plan is roughly twice the size it needs to be. Nine stages and fifteen issues collapse to five stages and eight issues without losing any user-visible capability. The oversizing is concentrated in three places: a five-table register with no consumer, a data-governance subsystem where a Python dict suffices, and a nested-route component folder where a ~110-line panel matches the existing pattern.

## What the plan gets right

The reuse thesis is not aspirational — it is already proven in the repo. [procurement_request.py:55-136](backend/app/workflows/procurement_request.py#L55-L136) is a genuine adapter ABC (9 class attributes, 7 abstract methods, 3 optional hooks) with nothing consultant-specific left in it. [contractor_procurement.py](backend/app/workflows/contractor_procurement.py) is **288 lines including the entire literal EOI document text** and duplicates zero engine code. Its whole registration diff was six one-liners across `runs.py`, `worker.py`, `workflow_capabilities.py`, `server.py`, and two frontend maps.

A third adapter is cheap. The plan's Stage 4 adapter and Stage 5 wiring are correctly sized. Everything below is about the rest.

Also correct: keeping Tender Comparison downstream and separate, refusing to insert generated artefacts into project evidence, forbidding LLM arithmetic in price schedules, and the negative-intent routing tests ("compare these quotes" must never queue a drafting run).

---

## Findings

### F1 — Stage 2: five tables where one will do

**Decision taken:** slim `procurement_requests` table only.

Drop `procurement_request_decisions`, `procurement_recipients`, `procurement_responses`, `procurement_response_files`, and all of Stage 7. Keep one table: project FK, kind, target name/slug, status, current draft FK, issue/close timestamps, `revision`, timestamps.

Evidence for dropping the decisions table specifically: [project_decision.py](backend/app/database/project_decision.py) already has `decision_id`, `options`, `selected`, `source`, `revision` (optimistic concurrency), `locked`, `evidence_conflict`, `agent_suggestion`, `provenance` — **and a `workflow_type` column**. [projects/decisions.py](backend/app/projects/decisions.py) is a complete 393-line service with conflict classes and event publication, already used by three workflows. The proposed `procurement_request_decisions` re-creates every one of those columns.

For v1, the plan's six "blocking issue decisions" become TBC lines inside the document, which is exactly what the EOI ships today — see [contractor_procurement.py:121-128](backend/app/workflows/contractor_procurement.py#L121-L128) and [:204](backend/app/workflows/contractor_procurement.py#L204) ("Close date/time and lodgement method: TBC by client before issue"). The user edits the draft before sending. If per-request decisions are genuinely wanted later, namespace `decision_id` as `trade_rfq_electrical:contract-form` and reuse the existing table — the only other change is one entry in `_DECISION_DRAFT_WORKFLOWS` ([api/projects.py:2011](backend/app/api/projects.py#L2011)).

**Removes:** PRQ-003, PRQ-010, PRQ-011, PRQ-012, and most of PRQ-002.

### F2 — Stage 1: the catalogue is a Python dict, not a data subsystem

**Decision taken:** free text + generic fallback.

The plan proposes `data/procurement/trade_packages.yaml` + `README.md` + `tools/validate.py` + a loader module + a test suite + a CI invocation, gated as a hard prerequisite before any generation work.

[normalise_discipline()](backend/app/workflows/consultant_procurement.py#L684-L706) already proves the cheaper pattern: normalise → alias map → curated profile → **generic fallback constructed from the raw name**. And [normalise_package()](backend/app/workflows/contractor_procurement.py#L36-L38) accepts literally any string today. So any trade name works from day one with no catalogue at all.

Start with a `TRADE_PACKAGES` dict of the trades actually tendered plus one generic profile, in the adapter module. No YAML, no loader, no validator, no CI step, no blocking gate.

Worth recording for when per-trade profiles are wanted: [data/tender/taxonomy.yaml](data/tender/taxonomy.yaml) holds ~200 coded packages in construction sequence and `synonyms.base.csv` / `synonyms.seed.csv` hold ~3,300 curated aliases. The plan's no-entanglement rule is about *code imports* — copying data would not violate it, and re-authoring 3,300 aliases by hand is the largest hidden cost in the original Stage 1. Scope prose already exists in [trade-interfaces-coordination-guide.md](data/seed/trade-interfaces-coordination-guide.md), [procurement-quoting-guide.md](data/seed/procurement-quoting-guide.md) and [procurement-tendering-guide.md](data/seed/procurement-tendering-guide.md).

One thing to *not* do: cost-plan rows are the wrong granularity. [cost_plan_lines.py](backend/app/sitewise/cost_plan_lines.py#L66-L76) gives residential nine elemental rows — "Building services" is one row, but you tender electrical, plumbing and HVAC separately. Useful for grouping the picker; not usable as package identity.

**Removes:** PRQ-001 as a standalone issue and its blocking gate.

### F3 — Stage 4: four new modules should be one new module plus two generalisations

**Decision taken:** both RFT and RFQ use the bounded narrative.

That makes generalisation more important, not less — otherwise there are three near-identical narrative modules.

| Plan proposes | Do instead |
| --- | --- |
| `trade_request_narrative.py` | Generalise [rfp_narrative.py](backend/app/workflows/rfp_narrative.py) (165 lines). It differs from a trade version only by output-model field set and a `DisciplineProfile` type hint. Widen the target type to `ProcurementTarget`, parameterise the field set and instructions path. One module serves RFP, RFT, RFQ. |
| `trade_request_evidence_validation.py` | Generalise [rfp_evidence_validation.py](backend/app/sitewise/rfp_evidence_validation.py) (53 lines). The citation logic is already field-agnostic; it is only typed to `RfpNarrativeOutput`. Generalise over a field list. |
| `trade_request_renderer.py` | Genuinely new — but **RFT and RFQ must be one renderer driven by a section list**, not two renderers. |
| `trade_request_narrative_instructions.md` | Keep, and add a second for the RFQ. These are content, and the length budget lives here. |

For the one-renderer-two-variants shape, the repo already has the pattern twice: [section_contracts.py:20-55](backend/app/sitewise/section_contracts.py#L20-L55) (`WORK_TYPE_HEADING_VARIANTS` + `document_title()` — literally "same engine, renamed/reduced section set") and [cost_plan_sources.py:42-46](backend/app/sitewise/cost_plan_sources.py#L42-L46) (`COST_PLAN_SECTIONS` tuple + `required_section_headings()`). Note [rfp_renderer.py:108-158](backend/app/sitewise/rfp_renderer.py#L108-L158) is currently a hardcoded list literal with headings and body copy interleaved — converting it to a section list is the real work in this area, and it pays for RFP, RFT and RFQ at once.

### F4 — "Keep the RFQ short" needs a mechanism, not an intention

The plan says RFQ "omits unnecessary formal sections" but gives no enforcement. Three levers, all cheap, all testable:

1. `max_pages` is already clamped at [procurement_request.py:181](backend/app/workflows/procurement_request.py#L181) (`min(max_pages, 3)`). EOI defaults to 1, consultant to 3. Set **RFQ = 1, RFT = 3**.
2. The RFQ section list is a strict subset of the RFT's — assert that relationship in a test so it can't drift.
3. State word budgets per narrative slot in the RFQ instructions file, and add a fixture test asserting the RFQ output is under a line count and omits the RFT-only headings.

Without (3) especially, "concise" degrades the first time the narrative prompt is tuned.

### F5 — Stage 3: most of the engine changes aren't needed

`sync_workspace` is **already an injectable parameter** ([procurement_request.py:178](backend/app/workflows/procurement_request.py#L178)) and the consultant adapter already uses it to get a different path shape ([consultant_procurement.py:896](backend/app/workflows/consultant_procurement.py#L896)). Package-specific workspace paths therefore need no engine edit at all.

The one genuine gap is provenance: the dict at [:262-269](backend/app/workflows/procurement_request.py#L262-L269) is hardcoded, so adding `procurement_request_id` / `request_kind` needs a ~5-line hook. That is justified.

Shared renderer atoms (project summary table, citation index, document-register table) are a real extraction and worth doing — but hold to the plan's own rule of extracting only what has two callers, and do it as part of the section-list refactor rather than as a separate gated stage.

### F6 — Frontend: no new route, no new component folder

The lean pattern is [ProjectControlBoard.tsx:729-813](frontend/src/components/project/ProjectControlBoard.tsx#L729-L813) — 85 lines:

```
[error line] → [OverlayGateNotice] → [WorkflowProgressStrip while running]
→ [1-2 primary buttons] → [WorkflowDraftPreview | DraftReviewPanel embedded]
→ [WorkflowTracePanel]
```

Commit `205d9ded` deliberately stripped the readiness-tile grid, risk-flag chips, next-actions block, per-tile `<header>` descriptions and the separate "Review draft" button. The new panel must not reintroduce any of them.

The one structural difference: PMP and Cost Plan have **one** draft each; procurement has **many** (one per target). So the panel needs a request selector that the others don't. Leanest shape:

```
[error line]
[OverlayGateNotice]
[WorkflowProgressStrip while running]
[ kind: RFP | RFT | RFQ ]  [ target: text input ]  [ Create ]
[ compact request list — latest draft per target, click to load ]
[ WorkflowDraftPreview while running | DraftReviewPanel embedded ]
[ WorkflowTracePanel ]
```

~110 lines in `ProjectControlBoard.tsx` plus one small list component. **No `/requests` route, no `App.tsx` change, no outlet-context widening, no `frontend/src/lib/queries/procurement.ts`.** [DraftReviewPanel](frontend/src/components/project/DraftReviewPanel.tsx) is already workflow-type-generic (its label and empty-message helpers fall back sensibly), so it renders a trade RFT today with no changes. [TenderRouteFrame.tsx](frontend/src/components/project/tender/TenderRouteFrame.tsx) and [ComparisonList.tsx](frontend/src/components/project/tender/ComparisonList.tsx) stay the models if a dedicated route is ever justified — which it isn't until there's a recipient/response register to house.

Note the plan's proposed "issue readiness" and "status controls" components would re-implement `OverlayGateNotice` / `CapabilityGateNotice`, which are currently private to `ProjectControlBoard.tsx` — extract, don't copy, if they're needed elsewhere.

### F7 — Don't split the `procurement` tile id

The plan replaces the `procurement` tile with `procurement-requests` + `tender-comparison`. That id is load-bearing in five places — [workflowTiles.ts:90](frontend/src/components/project/workflow/workflowTiles.ts#L90), [workflowRouting.ts:9-13](frontend/src/components/project/workflow/workflowRouting.ts#L9-L13), [ProjectControlBoard.tsx:690,714-718,980](frontend/src/components/project/ProjectControlBoard.tsx#L690), [ProjectCockpitPage.tsx:330-332,821,956](frontend/src/pages/ProjectCockpitPage.tsx#L330-L332) — including the `?artefact=` deep-link handler at [ProjectCockpitPage.tsx:311-344](frontend/src/pages/ProjectCockpitPage.tsx#L311-L344), plus two test files totalling 1,134 lines.

**Add a new tile instead and leave the existing one alone.** One object pushed into `buildLifecycleTiles` above the `procurement` entry gives the exact nav order the plan specifies — Project Profile, Project Plan, Cost Plan, RFP / RFT, Tender Comparison — and touches nothing existing. The left nav renders only icon + label, so `status`/`statusLabel`/`description` need minimal effort.

Separately, `workflowRouting.ts` has two live bugs worth fixing in the same pass: `consultant_procurement: "design"` points at a tile id that **does not exist**, and `rft: "procurement"` currently routes RFTs to Tender Comparison. Point `consultant_procurement`, `contractor_eoi`, `rft` and `rfq` at the new tile — 4 lines.

### F8 — Stage 8 display work is mostly widening prefix checks

Three pieces already exist and are either parameterised or dead-and-waiting:

- [get_latest_consultant_procurement_draft_summaries](backend/app/database/draft_artifacts.py#L156-L188) **already takes a `prefix` parameter** and works for any workflow family despite its name. Rename and call it for the procurement prefixes.
- [reconcileArtefactEvent](frontend/src/pages/ProjectCockpitPage.tsx#L196-L217) already gates on `workflowType.startsWith("consultant_procurement")` — widen the prefix.
- `isConsultantProcurementWorkspaceFile` / `isContractorEoiWorkspaceFile` in [workspaceRouting.ts:16,22](frontend/src/lib/workspaceRouting.ts#L16) are already written and imported nowhere.

The genuinely new piece is the discriminated `source | artefact` row type in [DocumentRepositoryPanel.tsx](frontend/src/components/project/DocumentRepositoryPanel.tsx) — schedule mode currently renders source evidence only. Worth noting this gap is not procurement-specific: PMP and cost-plan drafts don't appear in schedule mode either, so this work benefits all four workflows. The existing `UsageMarks` / `DocumentUsageMark` mechanism is the precedent for artefact↔evidence linkage in that table.

### F9 — Gaps the plan misses

**(a) Artefact editability — blocks the user's actual workflow.** [artefact_adapters.py](backend/app/projects/artefact_adapters.py#L81-L82) registers only `create_pmp`, `create_cost_plan` and `consultant_procurement`; everything else raises `ArtefactPolicyViolation`. **`contractor_eoi` was never added, so EOI drafts cannot be revised or accepted today.** Since the intended flow is generate → edit → copy into Outlook, trade RFT/RFQ must be registered here or the artefact is read-only. Two lines each — and fix the EOI omission at the same time.

**(b) Knowledge catalog blind spot.** [knowledge_catalog.py:34](backend/app/sitewise/knowledge_catalog.py#L34) — `WORKFLOWS` omits `head-contractor-procurement`, even though [contractor_procurement.py:22](backend/app/workflows/contractor_procurement.py#L22) uses that key and four seed files declare it in `required_by`. Retrieval still works, but the catalog-parity coverage tests silently skip it. Add both that key and the new trade workflow key, or the trade workflow inherits the same untested blind spot.

**(c) Misrouting guard.** `start_consultant_procurement` returns `{"kind": "blocked", "redirect": "start_contractor_eoi"}` for trade-shaped asks ([server.py:1431-1463](backend/app/mcp_bridge/server.py#L1431-L1463)). Once a trade tool exists, that redirect must point at it — otherwise "RFQ for the electrician" lands on a head-contractor EOI.

**(d) Dead code to delete before it gets copied.** `consultant_procurement.py` carries ~300 lines of never-called post-extraction duplication — `_retrieve_project_evidence` (:931), `_retrieve_platform_knowledge` (:960), `_project_evidence_item` (:1194), `_platform_knowledge_item` (:1210), `_source_trace` (:1276), `_platform_title` (:1393). The engine's copies win. Delete these before writing a third adapter, or they get copy-pasted.

**(e) Progress strip is a closed union.** `WorkflowProgressKind` is `"project_plan" | "cost_plan"` ([workflow-progress.ts:21](frontend/src/lib/workflow-progress.ts#L21)) with hardcoded phase arrays. Add a procurement kind (~20 lines) or the strip won't render.

### F10 — Export is deferred, deliberately

**Decision taken:** Markdown + copy button for v1.

Drafts are Markdown in storage; only the cost plan has a binary export ([draft_artifacts.py:51-62](backend/app/database/draft_artifacts.py#L51-L62), xlsx). `CopyContentButton` already exists in `DraftReviewPanel`. Recording the constraint plainly: **a trade will not accept a `.md` file**, so the real send path in v1 is copy-and-paste into Outlook or Word. Add `.docx` export (python-docx is already vendored, and the xlsx path is the precedent) once the document content has been red-penned and the formatting is worth locking in.

---

## Revised staging

Nine stages → five. The key sequencing change: **prove document quality end-to-end through chat before committing any schema or UI.** That is how the EOI shipped, and it front-loads the only genuinely risky part.

### Stage A — Trade RFT/RFQ generation, chat only

No table, no UI, no route. Deliver an adapter that generates both variants and publishes a normal draft artefact reachable from chat.

- Delete the dead duplication in `consultant_procurement.py` (F9d) **first**.
- Refactor [rfp_renderer.py](backend/app/sitewise/rfp_renderer.py) to a section list; add RFT and RFQ variants against it (F3).
- Generalise `rfp_narrative.py` and `rfp_evidence_validation.py` over target type and field set (F3).
- Create `backend/app/workflows/trade_procurement.py` — adapter + `TRADE_PACKAGES` dict + generic fallback, modelled on `contractor_procurement.py` and `normalise_discipline` (F2).
- Two instruction files with explicit length budgets; RFQ `max_pages=1`, RFT `max_pages=3` (F4).
- Add the ~5-line provenance hook in `procurement_request.py`; use the existing `sync_workspace` injection for package paths (F5).
- Wire the run type: `runs.py` `SUPPORTED_WORKFLOWS`, one `elif` in `worker.py`, `workflow_capabilities.py` entry, `_MCP_WORKFLOW_CAPABILITIES`, the ~25-line `start_trade_procurement` tool, `turn_context.py` / `workspace_instructions.py` routing text.
- Fix the `NonConsultantDiscipline` redirect (F9c) and `knowledge_catalog.WORKFLOWS` (F9b).
- Register both `trade_*` and the missing `contractor_eoi` in `artefact_adapters.py` (F9a).

**Gate:** four representative outputs (main-works RFT, structural steel RFT, electrical RFQ, custom specialist package) pass fixtures and a red-pen review. RFQ demonstrably short. No consultant or EOI fixture drift.

### Stage B — Slim requests table

One table, one migration with RLS, a thin service that creates/lists requests and attaches the current draft, and list/create/get + status-transition endpoints. No decisions, recipients, responses or file-link tables (F1).

### Stage C — RFP / RFT dashboard panel

One new tile in `buildLifecycleTiles` (F7), one branch in `WorkflowDetail` mirroring the PMP branch, one compact request list, the `workflowRouting.ts` fixes, and the progress-strip kind (F9e). No new route (F6).

### Stage D — Repository artefact rows

Widen the existing prefix checks and add the discriminated `source | artefact` schedule row (F8). Cover PMP and cost-plan drafts in the same change since they have the identical gap.

### Stage E — Backfill and acceptance

Idempotent backfill creating one request row per existing consultant/EOI draft lineage pointing at the latest draft. No recipients, responses or decisions to derive, so this is materially smaller than the original Stage 9. Then the acceptance scenarios — keeping the plan's negative-intent test ("compare the three roofing quotes" must not queue a drafting run) and the tenancy test, which are both well-judged.

**Issue split:** PRQ-001/003/010/011/012 disappear; PRQ-002 shrinks to one table. Roughly eight issues, not fifteen.

## Verification

Backend, from `backend/`:

```powershell
uv run pytest tests/workflows tests/sitewise tests/mcp_bridge tests/agent -q
uv run pytest tests/workflows/test_consultant_procurement.py tests/sitewise/test_rfp_renderer.py -q
uv run pytest tests/test_project_cockpit_bootstrap.py tests/test_project_draft_versioning.py -q
uv run ruff check app tests
```

The consultant RFP and contractor EOI suites are the regression gate for the renderer refactor — run them explicitly and confirm byte-identical fixtures before any trade work merges.

Frontend, from `frontend/`:

```powershell
pnpm test
pnpm tsc --noEmit
pnpm lint
```

Run `ProjectControlBoard.test.tsx`, `ProjectCockpitPage.test.tsx`, `workflowTiles.test.ts` and `DraftReviewPanel.test.tsx` explicitly before the full suite.

End-to-end: use the repo's `verify` skill recipe (dev stack handles, isolated test user, Playwright). Drive one full pass — chat-queue an electrical RFQ, watch the progress strip, open the completed draft in the panel, edit a section, copy the content out. That last step is the real acceptance criterion, since copy-to-Outlook is the v1 send path.

## Deferred, with the migration path recorded

- **Recipients and responses.** The slim requests table is the anchor; the register tables attach to it later without reshaping anything.
- **Per-request blocking decisions.** Reuse `project_decisions` with a namespaced `decision_id` plus one entry in `_DECISION_DRAFT_WORKFLOWS`; no new table.
- **Trade package catalogue.** Grow `TRADE_PACKAGES` from real use. `data/tender/taxonomy.yaml` and the ~3,300 alias rows are the source if a bulk import is ever wanted.
- **`.docx` export.** python-docx is vendored; the cost-plan xlsx path is the precedent.
- **Dedicated `/requests` route.** Justified once there's a recipient/response register to house; `TenderRouteFrame` is the model.
