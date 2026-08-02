# Procurement Requests (RFP, RFT, and RFQ) — Lean Implementation Plan

**Date:** 2026-08-02
**Product specification:**
[Procurement Requests PRD](../issues/procurement-requests/README.md)
**Peer review:**
[Procurement Requests implementation-plan review](./2026-08-02-procurement-requests-rfp-rft-rfq-review.md)
**Status:** Revised after peer review; ready for issue creation.

## Goal

Extend Clerk’s proven consultant-procurement engine so a user can prepare:

- consultant requests for fee proposal;
- head-contractor expressions of interest;
- full trade, supplier, specialist, or main-works RFTs; and
- genuinely concise trade or supplier RFQs.

The v1 workflow is generate, review, edit, and copy into Outlook or Word. It
does not send documents, manage contacts, receive tenders, or award work.

The latest generated artefacts must be visible in both repository tree and
schedule modes. Tender Comparison remains a separate downstream workflow with
its current ownership boundary and URLs.

## Delivery Strategy

Prove the document and chat workflow before adding schema or UI:

```text
project snapshot + project evidence + platform guidance
    -> existing ProcurementDocument engine
    -> trade adapter with RFT/RFQ section contract
    -> deterministic scaffold + bounded narrative
    -> citation/completeness validation
    -> normal draft artefact + workspace file
    -> chat review/edit/copy
    -> slim request record
    -> lightweight cockpit panel
    -> repository schedule row
```

The quality of the generated document is the risky part. Stages therefore run
in this order:

1. generation and chat;
2. one slim requests table;
3. one lightweight dashboard panel;
4. repository artefact rows; and
5. backfill and acceptance.

## Binding V1 Decisions

- Left-nav order is Project Profile, Project Plan, Cost Plan, RFP / RFT, Tender
  Comparison.
- Add a new RFP / RFT tile. Keep the existing `procurement` tile ID and
  Tender Comparison routes unchanged.
- The RFP / RFT experience remains inside `ProjectControlBoard.tsx`; v1 adds
  no `/requests` route.
- The panel is deliberately small: kind, free-text target, create action,
  compact request list, current draft, progress, and trace.
- Consultant RFP and contractor EOI outputs retain their current behaviour.
- Trade RFT/RFQ extends `ProcurementDocument`; it does not duplicate retrieval,
  versioning, provenance, storage, or workspace publication.
- Both RFT and RFQ use bounded, evidence-grounded narrative with a three-page
  nominal target. This is guidance for clear drafting, not an output limit.
- RFQ and RFT share the same core document coverage. The RFQ may use lighter
  formality where suitable, but neither its structure nor its output length is
  rejected for exceeding a page or line limit.
- V1 trade coverage is free text plus a small in-code `TRADE_PACKAGES` profile
  map and generic fallback. There is no YAML catalogue, loader, validator, or CI
  gate.
- Unknown non-empty trade names are valid. The fallback may organise supplied
  and evidenced information but never invent specialist scope.
- Cost-plan elements may group suggestions but are not package identities.
- The existing Project Summary renderer is reused.
- Price and returnable schedules are deterministic blank templates. An LLM
  performs no arithmetic.
- Only one new table, `procurement_requests`, is introduced in v1.
- Per-request decision tables and controls are deferred. Unresolved issue inputs
  render as visible TBC lines and are edited in the draft.
- Recipient, contact, response, and response-file tables and UI are deferred.
  Users send and receive through their existing Outlook/document workflow.
- Creating a request produces Markdown. `DraftReviewPanel` provides the v1
  copy action. DOCX export is deferred.
- Generated requests remain artefacts and never become project evidence merely
  to appear in schedule mode.
- Schedule mode gains a general `source | artefact` row contract. The same
  work also exposes Project Plan and Cost Plan drafts because they have the
  identical presentation gap.
- No new runtime dependency is expected.

## V1 and Deferred Scope

| Deliver now | Explicitly defer |
| --- | --- |
| Chat-triggered consultant RFP, trade RFT, and trade RFQ | Email/Outlook integration or automatic issue |
| Existing head-contractor EOI continuity | Recipient/contact directory |
| Small curated trade profiles plus free-text fallback | Governed YAML trade catalogue |
| Deterministic RFT and short RFQ templates | External tender lodgement |
| Edit, accept, and copy Markdown | DOCX export |
| Slim request history and status | Response and revision register |
| Lightweight cockpit panel | Dedicated `/requests` route |
| Artefacts in repository schedule mode | Per-request decision UI |
| Idempotent legacy backfill | Award, contract, or cost-plan handoff |

Each deferred item has a migration path under **Deferred Evolution** below.

## Current-State Anchors and Confirmed Gaps

- `backend/app/workflows/procurement_request.py` is already the shared engine.
  Its `sync_workspace` callback is injectable, so package paths require no new
  engine hook.
- The same engine hard-codes provenance metadata. A small adapter hook is needed
  for request ID and request kind.
- `backend/app/workflows/consultant_procurement.py` is the quality reference,
  but it contains an unused duplicate retrieval/helper chain. Remove that chain
  before adding a third adapter so it is not copied.
- `backend/app/workflows/contractor_procurement.py` proves a compact second
  adapter can reuse the engine without duplication.
- `backend/app/sitewise/rfp_renderer.py` interleaves headings and body in a
  fixed list. Refactoring that list into section contracts is the shared seam.
- `backend/app/workflows/rfp_narrative.py` and
  `backend/app/sitewise/rfp_evidence_validation.py` are structurally generic
  but typed to consultant output. Generalise them instead of cloning them.
- `backend/app/projects/artefact_adapters.py` omits contractor EOI and would
  reject edit/accept operations for EOI and new trade artefacts.
- `backend/app/sitewise/knowledge_catalog.py` omits the existing
  `head-contractor-procurement` key from its parity list.
- `backend/app/mcp_bridge/server.py` currently redirects a trade-shaped
  consultant request to head-contractor EOI. It must redirect to trade
  procurement after that tool exists.
- `frontend/src/components/project/workflow/workflowRouting.ts` points
  consultant procurement at a non-existent tile and RFT at Tender Comparison.
- `frontend/src/lib/workflow-progress.ts` has a closed Project Plan/Cost Plan
  union and needs a procurement progress kind.
- `backend/app/database/draft_artifacts.py` already has a prefix-parameterised
  latest-procurement query despite its consultant-specific name.
- `frontend/src/pages/ProjectCockpitPage.tsx` already reconciles artefact
  events; its workflow-family checks only need widening.
- `frontend/src/components/project/workflow/workspaceRouting.ts` already has
  consultant and contractor workspace classifiers that can be used and extended
  for trade paths.
- `frontend/src/components/project/DocumentRepositoryPanel.tsx` currently
  renders schedule mode from source evidence only.

## Domain Contracts

### Request kinds

| Kind | Target | Length | Implementation |
| --- | --- | --- | --- |
| `consultant_rfp` | Consultant discipline | Existing limit | Existing consultant adapter |
| `contractor_eoi` | Head contractor or builder | Existing one-page output | Existing EOI adapter |
| `trade_rft` | Main works, trade, supplier, or specialist | Three-page nominal target | New trade adapter |
| `trade_rfq` | Defined trade, supply, or service package | Three-page nominal target | Same trade adapter, lighter formality where appropriate |

### Request lifecycle

```text
draft -> issued -> closed
   \        \
    +-------> cancelled
```

- `draft`: working artefact prepared for user review.
- `issued`: user records that issue occurred outside Clerk.
- `closed`: user records the request period as closed.
- `cancelled`: request abandoned without deleting history.

There is no `ready_for_issue` state in v1 because Clerk does not maintain a
separate issue-decision model. Visible TBC items remain part of the Markdown
review workflow. No status transition sends a document.

### Slim request row

`procurement_requests` contains only:

- ID, project FK, and creator user FK;
- request kind;
- target name and normalised target slug;
- status;
- current draft artefact FK;
- issued and close timestamps;
- optimistic revision; and
- created/updated timestamps.

The service validates lifecycle changes and same-project draft attachment.
Document provenance remains the detailed audit source.

### Trade target profile

The trade adapter owns a small immutable profile type with:

- canonical display name and aliases;
- optional construction-sequence group;
- baseline scope/interface prompts;
- deterministic price-breakdown lines; and
- applicable returnables.

`normalise_trade_target(raw_name)` performs:

1. trim and normalise;
2. resolve a curated alias if present;
3. return a curated profile if present; otherwise
4. construct a generic profile from the user’s non-empty name.

The initial map covers only frequently tendered packages needed for fixtures and
early use. It grows from observed product need.

### Document contracts

RFT and RFQ use one renderer driven by ordered section lists. Both cover the
same core procurement information; variants tailor tone and optional formality,
not a hard length quota.

RFT includes:

- Project Summary;
- invitation/package basis;
- issued-document schedule;
- scope and interfaces;
- programme and tender timetable;
- deterministic price breakdown;
- returnables;
- departures, qualifications, and exclusions;
- RFI/addendum and submission controls; and
- draft/TBC review items.

RFQ includes the same core information in a quotation-oriented form:

- Project Summary;
- package and issued documents;
- concise scope/interfaces;
- delivery or lead-time requirement;
- deterministic quotation breakdown;
- exclusions, qualifications, and validity; and
- submission details/TBC review items.

The renderer owns headings, tables, price rows, returnable rows, and
placeholders. Bounded narrative owns only short project/package context,
evidence-grounded scope/interface tailoring, and programme/lead-time context.

### Workspace paths

Existing consultant and EOI paths do not change. New trade drafts use:

```text
05-procurement/<target name>/02-tender-pack/
  <target_slug>_<rft|rfq>_vNN.draft.md
```

Use the existing injectable workspace-sync callback and current path
canonicalisation/traversal checks.

## Stage A — Trade Generation Through Chat

**Outcome:** A real chat turn generates an editable RFT or demonstrably short
RFQ and publishes a normal draft artefact. No new table or dashboard is needed
to prove the vertical slice.

### A1. Remove duplication before extension

Delete the unused post-extraction helper chain from
`backend/app/workflows/consultant_procurement.py`, including its private
retrieval, evidence-item, platform-item, source-trace, and title helpers.

Prove the helpers are unreferenced, then run consultant fixtures before any
renderer change.

### A2. Refactor the shared content seam

- Convert `backend/app/sitewise/rfp_renderer.py` to an ordered section
  contract rather than a hard-coded interleaved list.
- Extract shared Project Summary, citation index, and document-register atoms
  only when both consultant and trade renderers call them.
- Generalise `backend/app/workflows/rfp_narrative.py` over a
  procurement-target contract and requested output fields.
- Generalise
  `backend/app/sitewise/rfp_evidence_validation.py` over an explicit
  narrative-field list.
- Keep consultant fee/stage wording in the consultant renderer.
- Keep EOI wording inside the EOI adapter.
- Do not build a configurable mega-template.

Existing consultant RFP and contractor EOI fixtures are the regression gate.
Where the current suite uses golden output, the refactor must remain
byte-identical.

### A3. Add one trade adapter and one variant renderer

Create:

- `backend/app/workflows/trade_procurement.py`;
- `backend/app/sitewise/trade_request_renderer.py`;
- `backend/app/workflows/trade_rft_narrative_instructions.md`; and
- `backend/app/workflows/trade_rfq_narrative_instructions.md`.

The adapter contains the initial `TRADE_PACKAGES` map and generic fallback.
Both variants call one renderer with different section lists and instructions.

Enforce:

- RFT and RFQ both use a three-page nominal target;
- the generator treats that target as concision guidance and completes a
  document that reasonably needs to run longer;
- RFQ instructions use quotation-oriented, direct language without deleting
  core scope, price, returnable, or submission coverage;
- assigned citation tokens for project-specific narrative;
- no unknown or uncited project-specific claims;
- deterministic blank/TBC commercial cells; and
- generic fallback scope no broader than user instructions and cited evidence.

Add only a small provenance hook to
`backend/app/workflows/procurement_request.py`. Use the already-injected
`sync_workspace` callback for the package path.

### A4. Wire the durable workflow and chat

Update the existing registration seams:

- `backend/app/workflows/runs.py`;
- `backend/app/workflows/worker.py`;
- `backend/app/projects/workflow_capabilities.py`;
- `backend/app/api/projects.py`;
- `backend/app/mcp_bridge/server.py`;
- `backend/app/agent/turn_context.py`; and
- `backend/app/agent/workspace_instructions.py`.

Add `start_trade_procurement` with project-scoped authorization, idempotency,
kind, target, and concise optional instructions. Reuse the normal durable run,
worker, SSE, and artefact event contract.

Routing rules:

- consultant services/fee proposal -> consultant procurement;
- RFT/invite to tender/trade or contractor tender -> trade RFT;
- RFQ/request for quotation/quote a defined package -> trade RFQ;
- head-contractor shortlist/EOI -> contractor EOI;
- compare/evaluate/normalise/recommend/select/award existing responses -> Tender
  Comparison or its capability response, never drafting; and
- ambiguous “request for services” -> one concise clarification before queuing.

Also:

- redirect `NonConsultantDiscipline` to the new trade tool rather than
  `start_contractor_eoi`;
- add `head-contractor-procurement` and the new trade workflow key to
  `knowledge_catalog.WORKFLOWS`;
- register contractor EOI and both trade kinds in
  `backend/app/projects/artefact_adapters.py` so revise and accept work; and
- add procurement capability/progress metadata without importing from
  `backend/tender/`.

### Stage A tests and gate

Add or extend tests for:

- shared section ordering and consultant fixture stability;
- generalised narrative and citation validation;
- RFT/RFQ section contracts and length controls;
- custom-package fallback;
- durable-run dispatch, idempotency, retry, cancellation, and publication;
- MCP authorization and trade-shaped consultant redirect;
- chat positive and negative intent routing;
- knowledge-catalog parity; and
- revise/accept policy for contractor EOI, RFT, and RFQ.

Red-pen these four outputs against project evidence:

1. main-works RFT;
2. structural-steel RFT;
3. electrical RFQ; and
4. custom specialist package.

The stage passes only when the electrical RFQ is complete, proportionate to the
RFT, and clear without arbitrary truncation; all four documents are editable;
and consultant RFP/contractor EOI tests show no drift.

## Stage B — Slim Procurement Requests Table

**Outcome:** Generated requests have a durable, project-scoped list identity
without recipients, responses, or decision infrastructure.

### Data and service

- Add one SQLAlchemy model for `procurement_requests`.
- Add one Alembic migration with FKs, constrained kind/status values, useful
  project/list indexes, RLS, grants, and project-owner policies.
- Add a small Clerk-core service for create, get, list, current-draft
  attachment, and status transition.
- Add project API schemas and list/create/get/status endpoints using current
  ownership, entitlement, and response conventions.
- Integrate run start/publication so UI-created requests receive the published
  draft. Preserve idempotency when the same run is retried.

Do not add:

- `procurement_request_decisions`;
- `procurement_recipients`;
- `procurement_responses`;
- `procurement_response_files`; or
- rollups/readiness calculations with no v1 consumer.

### Stage B tests and gate

Tests cover:

- model constraints, migration upgrade, indexes, FKs, RLS, and grants;
- owner A cannot read or mutate owner B’s rows or drafts;
- valid and invalid lifecycle transitions;
- optimistic request revision conflicts;
- same-project current-draft attachment;
- idempotent workflow attachment; and
- list order/current-draft summaries.

The stage passes when chat and API generation create or attach exactly one
current request row without changing artefact lineage.

## Stage C — Lightweight RFP / RFT Dashboard Panel

**Outcome:** The cockpit gains the requested nav item and a compact creation/list
panel without a new route or another frontend subsystem.

### Navigation and routing

- Add one new tile immediately before the existing `procurement` tile in
  `frontend/src/components/project/workflow/workflowTiles.ts`.
- Give the new tile a distinct ID such as `procurement-requests` and the label
  **RFP / RFT**.
- Leave the existing `procurement` ID, Tender Comparison tile, `/tender`
  routes, deep links, and browser history untouched.
- Fix `frontend/src/components/project/workflow/workflowRouting.ts` so
  `consultant_procurement`, `contractor_eoi`, `rft`, and `rfq` select the
  new tile while evaluation/recommendation remain on `procurement`.

### Panel shape

Implement one `WorkflowDetail` branch in
`frontend/src/components/project/ProjectControlBoard.tsx` using the same lean
pattern as current Project Plan and Cost Plan panels:

```text
[error]
[OverlayGateNotice]
[WorkflowProgressStrip while running]
[kind: RFP | RFT | RFQ] [target: text] [Create]
[compact latest-request list]
[WorkflowDraftPreview while running | DraftReviewPanel]
[WorkflowTracePanel]
```

Create at most one small request-list component. Keep the panel branch near
110 lines and do not add:

- a nested route or `App.tsx` changes;
- a procurement component folder;
- readiness tiles, risk chips, next-action cards, or duplicate headers;
- package-picker infrastructure;
- issue-readiness or status-control components; or
- a separate frontend query layer unless the existing API surface cannot
  express the calls clearly.

RFP delegates to the existing consultant workflow. RFT/RFQ delegates to the
trade workflow. Existing EOI requests appear in the list and remain chat
creatable.

Add `procurement` to `WorkflowProgressKind` with its phase labels so the
existing progress strip renders for the new workflow.

Reuse `DraftReviewPanel` for view, edit, accept, and copy. If gate notices must
be shared outside `ProjectControlBoard.tsx`, extract the existing component
rather than copying it.

### Stage C tests and gate

Update:

- `ProjectControlBoard.test.tsx`;
- `ProjectCockpitPage.test.tsx`;
- `workflowTiles.test.ts`;
- `workflowRouting.test.ts`;
- `workflow-progress.test.ts`; and
- `DraftReviewPanel.test.tsx` only if its generic fallback needs coverage.

Assert exact nav order, distinct tile identities, corrected artefact routing,
create/error/running/completed states, request selection, edit/accept, and copy.

The stage passes when an electrical RFQ can be created, observed, selected,
edited, and copied without leaving the cockpit panel.

## Stage D — Repository Artefact Rows

**Outcome:** Schedule and tree users can open generated drafts without changing
their evidentiary identity.

### Backend widening

- Rename/generalise
  `get_latest_consultant_procurement_draft_summaries` in
  `backend/app/database/draft_artifacts.py` and use its existing prefix
  capability for consultant, contractor EOI, and trade workflow families.
- Extend cockpit bootstrap/workspace self-heal to return the latest artefact
  summaries needed by schedule mode.
- Include Project Plan and Cost Plan artefacts in the same response contract
  because they have the same schedule-mode gap.

### Frontend row contract

Introduce a discriminated presentation row in
`frontend/src/components/project/DocumentRepositoryPanel.tsx`:

- `source`: current evidence preview, selection, usage marks, and deletion;
- `artefact`: draft ID, workflow type, title, version, path, label, status, and
  update time.

Artefact behaviour:

- click opens `DraftReviewPanel` through draft identity/path;
- latest revision appears in schedule mode;
- historical revisions remain available in tree mode;
- labels distinguish Project Plan, Cost Plan, RFP, EOI, RFT, and RFQ;
- artefacts never enter source selection, source deletion, or Tender Comparison
  evidence selection; and
- live artefact events add or replace the relevant latest row.

Widen `reconcileArtefactEvent` and related workflow-prefix checks in
`ProjectCockpitPage.tsx`. Use the existing workspace classifiers in
`frontend/src/components/project/workflow/workspaceRouting.ts` and add the
trade classifier beside them.

### Stage D tests and gate

Extend backend bootstrap/draft-versioning tests and:

- `DocumentRepositoryPanel.test.tsx`;
- `ProjectCockpitPage.test.tsx`; and
- `workspaceRouting.test.ts`.

Assert source interactions are unchanged, artefacts cannot enter evidence
actions, live events reconcile rows, and the same latest draft opens from chat,
dashboard, tree, and schedule.

## Stage E — Backfill, Acceptance, and Rollout

**Outcome:** Existing procurement artefacts appear in the slim request history,
and the complete draft/edit/copy workflow is proven before release.

### Idempotent backfill

Create an application backfill command/script that:

- scans consultant-procurement and contractor-EOI draft families;
- groups by project and trusted workflow lineage;
- creates one request row per lineage when absent;
- derives kind/target from provenance first and workflow suffix second;
- points at the latest draft while retaining all existing versions and paths;
- records conflicts and counts; and
- produces zero duplicates on rerun.

Do not infer recipients, responses, decisions, or issue dates.

### Automated verification

Backend, from `backend/`:

```powershell
uv run pytest tests/workflows tests/sitewise tests/mcp_bridge tests/agent -q
uv run pytest tests/workflows/test_consultant_procurement.py tests/workflows/test_consultant_procurement_golden.py tests/workflows/test_contractor_eoi.py tests/sitewise/test_rfp_renderer.py -q
uv run pytest tests/test_project_cockpit_bootstrap.py tests/test_project_draft_versioning.py -q
uv run ruff check app tests
```

Frontend, from `frontend/`:

```powershell
pnpm test
pnpm tsc --noEmit
pnpm lint
```

Run the focused cockpit, routing, workflow-tile, progress, draft-review, and
repository tests explicitly before the full frontend suite.

### Acceptance scenarios

1. Chat creates a consultant fee proposal with existing output unchanged.
2. Chat creates a structural-steel RFT with cited scope, interfaces, price
   schedule, and visible TBC issue inputs.
3. Chat creates an electrical RFQ with complete core procurement coverage and
   proportionate, quotation-oriented language.
4. A custom specialist request remains generic and flags missing scope.
5. “Compare the three roofing quotes” never queues a drafting workflow.
6. A second user/project cannot access the first project’s request or draft.
7. Existing RFP/EOI artefacts backfill once and open from intended surfaces.
8. The user opens the electrical RFQ in the cockpit, edits a section, accepts
   the revision, and copies the content for Outlook or Word.
9. Project Plan and Cost Plan drafts also appear in schedule mode without
   becoming evidence rows.

The edit-and-copy pass is the user-visible v1 acceptance criterion.

### Rollout

- Apply the one-table migration.
- Deploy generation and chat only after Stage A’s red-pen gate passes.
- Run the backfill and retain its report.
- Complete acceptance on a non-production project.
- Add the tile after API and backfill readiness.
- Monitor workflow failures, unmatched legacy artefacts, and schedule-row
  reconciliation.

Do not add a speculative feature flag unless an existing phase gate or deployment
sequence requires it.

## Deferred Evolution

### Recipients and responses

If users later need an in-product receipt register, attach recipient, response,
and response-file tables to `procurement_requests`. The slim v1 row remains
the anchor; no v1 table needs reshaping.

### Per-request decisions

Reuse `project_decisions` with namespaced IDs such as
`trade_rfq_electrical:contract-form` and add the workflow family to
`_DECISION_DRAFT_WORKFLOWS`. Do not introduce a duplicate decisions table.

### Governed trade catalogue

Grow `TRADE_PACKAGES` from real use. If bulk curation becomes worthwhile,
`data/tender/taxonomy.yaml` and the existing synonym datasets may inform a
copied, Clerk-core dataset. Never import TCM implementation code at runtime.

### DOCX export

Add after content has passed repeated red-pen review and formatting is stable.
The cost-plan binary export path is the precedent; the required document library
is already available, so no new dependency should be necessary.

### Dedicated requests route

Introduce only when the product has enough request detail—such as recipients
and responses—to justify a standalone workspace. `TenderRouteFrame` is the
reference at that point.

## Cross-Cutting Rules

- Authorize every API and MCP operation against the project.
- Preserve turn-token project binding for agent tools.
- Keep workflow starts idempotent and snapshot-bound.
- Keep source evidence and generated artefacts as distinct identities.
- Use project evidence for project facts and platform knowledge only as labelled
  guidance.
- Bound custom-package narrative to user input and cited evidence.
- Perform all price arithmetic deterministically outside the LLM.
- Canonicalise and validate every workspace/storage path.
- Regression-protect consultant RFP and contractor EOI output and editability.
- Keep Clerk core independent of `backend/tender/`.
- Add no dependency unless it satisfies repository policy.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| RFQ becomes unclear or over-formal | Shared core coverage, quotation-oriented instructions, and construction-professional red-pen review without length rejection |
| Unknown trade is rejected | Accept any non-empty target and construct a generic profile |
| Generic scope invents specialist obligations | Limit narrative to user instruction, curated prompts, and cited project evidence; show TBC gaps |
| RFT drafting is confused with comparison | Separate tiles/tools plus negative-intent routing tests |
| Shared refactor changes consultant output | Byte-identical consultant fixtures before trade generation merges |
| Generated artefact cannot be edited | Register EOI/RFT/RFQ in the existing artefact policy during Stage A |
| Platform guidance parity silently skips workflows | Add existing EOI and new trade keys to the knowledge catalogue tests |
| Dashboard repeats removed cockpit complexity | One in-place branch and one small list component; no route or component subsystem |
| Schedule rows become evidence | Discriminated row type and explicit exclusion from evidence actions |
| Slim table later proves insufficient | Deferred schemas attach by FK to the request anchor without changing v1 identity |
| Markdown is mistaken for a sendable tender file | Make copy-to-Outlook/Word explicit; defer DOCX until format is stable |

## Peer-Review Disposition

| Finding | Disposition in this plan |
| --- | --- |
| F1: five tables where one will do | Adopted: one slim request table; decisions/recipients/responses deferred |
| F2: catalogue is a dict, not a subsystem | Adopted: small in-adapter profiles plus free-text generic fallback |
| F3: generalise narrative and validation | Adopted: one trade renderer, two section variants, shared generalised narrative/validation |
| F4: enforce RFQ concision | Superseded by product direction: RFT and RFQ have comparable coverage and a three-page nominal target, with no hard output cap |
| F5: engine changes are mostly unnecessary | Adopted: existing workspace injection retained; only provenance hook added |
| F6: no new frontend route/folder | Adopted: lean in-place cockpit branch plus one small list component |
| F7: do not split `procurement` tile ID | Adopted: add a new tile; preserve Tender Comparison identity and routes; fix routing bugs |
| F8: schedule work is mostly widening | Adopted: generalise existing query/checks and add only the required discriminated row |
| F9: editability, catalogue, redirect, dead code, progress gaps | Adopted in Stage A/C with explicit tests |
| F10: Markdown and copy for v1 | Adopted; DOCX has a recorded migration path |

No review finding is rejected. Repository inspection corrected one cited frontend
path: the workspace routing helpers live under
`frontend/src/components/project/workflow/workspaceRouting.ts`, not
`frontend/src/lib/workspaceRouting.ts`.

## Implementation Issue Split

| Issue | Vertical slice | Depends on |
| --- | --- | --- |
| PRQ-001 | Remove dead consultant helpers; section-contract renderer and generalised narrative/citation validation with no fixture drift | none |
| PRQ-002 | Trade adapter, profiles/fallback, RFT/RFQ renderer, length contracts, and red-pen fixtures | PRQ-001 |
| PRQ-003 | Durable trade run, MCP/chat routing, provenance, knowledge parity, and EOI/trade editability | PRQ-002 |
| PRQ-004 | Slim request model, migration/RLS, service/API, and draft attachment | PRQ-003 |
| PRQ-005 | New tile, lean dashboard panel, routing fixes, and procurement progress | PRQ-004 |
| PRQ-006 | General source/artefact schedule rows for procurement, Project Plan, and Cost Plan | PRQ-005 |
| PRQ-007 | Idempotent legacy backfill and rollout checks | PRQ-004, PRQ-006 |
| PRQ-008 | End-to-end edit/copy acceptance, tenancy test, and final red-pen gate | all prior |

Create these as local Markdown issues after product sign-off. Use
`ready-for-agent` for independently implementable code slices and
`ready-for-human` for construction red-pen and release acceptance.

## Definition of Done

- Chat produces evidence-grounded consultant RFP, trade RFT, and short trade RFQ
  artefacts while preserving contractor EOI.
- RFT and RFQ use a three-page nominal target without length-based rejection;
  both retain complete core procurement coverage.
- Custom trade names work without fabricated specialist scope.
- Documents use the existing Project Summary and deterministic price schedules.
- Every RFT/RFQ can be opened, revised, accepted, and copied.
- The slim request history is project-secure and backfilled idempotently.
- RFP / RFT appears immediately before the unchanged Tender Comparison tile.
- The cockpit panel remains lean and requires no new route.
- Latest Project Plan, Cost Plan, RFP, EOI, RFT, and RFQ artefacts appear and
  open in schedule and tree modes without becoming evidence.
- Chat reliably distinguishes drafting from comparison/evaluation.
- Consultant RFP and contractor EOI regression suites remain green.
- Backend, frontend, tenancy, manual red-pen, and edit/copy acceptance gates are
  recorded before rollout.
