# Procurement Requests (RFP, RFT, and RFQ) — Staged Implementation Plan

**Date:** 2026-08-02  
**Product specification:**
[Procurement Requests PRD](../issues/procurement-requests/README.md)  
**Status:** Proposed for implementation; PRD is in `needs-triage`.

## Goal

Extend Clerk’s existing consultant procurement capability into a single
agent-first Procurement Requests workflow that can prepare consultant RFPs,
head-contractor EOIs, and trade/supplier RFTs or RFQs; retain a durable record of
recipients and responses; and expose the latest request artefacts consistently
in both document repository views.

The implementation must work across Clerk’s supported residential, commercial,
multi-residential, industrial, fitout, extension, refurbishment, and remediation
profiles. It must not broaden or entangle the Tender Comparison Module.

## Architecture

Clerk already has the correct generation spine:

```text
project snapshot + project evidence + platform guidance
    -> ProcurementDocument adapter
    -> deterministic scaffold + bounded narrative
    -> validation
    -> draft_artifact revision
    -> Supabase Storage export + workspace_files row
    -> chat artefact event / cockpit review
```

The feature adds three deep modules around that spine:

1. **Trade package catalogue** — resolves canonical packages, aliases,
   applicability, delivery modes, scope prompts, price-breakdown lines, and
   returnables through a small read-only interface.
2. **Procurement register service** — owns requests, request-scoped decisions,
   recipients, response revisions, and response-file links behind a
   project-authorized service interface.
3. **Trade request document adapter** — supplies RFT/RFQ-specific evidence
   queries, guidance selection, deterministic structure, narrative slots,
   validation, and package-specific workspace paths to the existing procurement
   engine.

The React surface consumes those interfaces through JSON APIs and the existing
durable workflow/SSE event vocabulary. Tender Comparison remains downstream and
separate.

## Binding Decisions

- Left navigation order is Project Profile, Project Plan, Cost Plan, RFP / RFT,
  Tender Comparison.
- The new route is `/projects/:projectId/requests`; existing `/tender` routes do
  not change.
- RFQ is a concise trade-request variant inside RFP / RFT, not another nav item.
- The existing consultant RFP and contractor EOI workflows retain their current
  output behaviour while becoming visible in the new register.
- Trade RFT/RFQ drafts extend `ProcurementDocument`; no parallel retrieval,
  versioning, provenance, or workspace engine is permitted.
- Trade catalogue data belongs to Clerk core, not `backend/tender/` or
  `data/tender/`.
- “All trades” means a reviewed common catalogue plus a custom-package fallback.
  The fallback never invents specialist scope.
- The existing Project Summary renderer is reused exactly.
- RFT/RFQ project-specific claims require project-document citations.
- Price schedules are deterministic blank returnables. An LLM performs no
  arithmetic.
- Creating a request produces a draft only. External issue/distribution remains
  a recorded human act in v1.
- Blocking issue decisions are scoped to one procurement request, not stored as
  project-global PMP decisions.
- The schedule view shows the latest revision of each procurement request. The
  tree remains the version-complete view.
- Generated requests remain artefacts. They are never inserted into project
  evidence merely to make the schedule render them.
- No new runtime dependency is expected.

## Current-State Anchors

- `backend/app/workflows/procurement_request.py` already owns the shared request
  engine: evidence retrieval, platform guidance, forecasts, provenance, draft
  publication, storage upload, and workspace row sync.
- `backend/app/workflows/consultant_procurement.py` is the mature RFP adapter and
  quality reference.
- `backend/app/workflows/contractor_procurement.py` proves a second deterministic
  procurement document can reuse the engine.
- `backend/app/sitewise/rfp_renderer.py` and the RFP narrative/validation modules
  establish the deterministic-scaffold plus bounded-narrative method.
- `backend/app/workflows/runs.py` and `worker.py` provide durable asynchronous
  execution, leases, retries, cancellation, idempotency, and result publication.
- `backend/app/mcp_bridge/server.py` already exposes consultant procurement and
  contractor EOI actions with project-scoped authorization.
- `frontend/src/components/project/DocumentRepositoryPanel.tsx` renders schedule
  mode from evidence rows only and tree mode from workspace paths; this is the
  source of the current visibility mismatch.
- `frontend/src/pages/ProjectCockpitPage.tsx` already receives evidence,
  workspace tree, and latest draft summaries in its bootstrap response.
- `data/project-template/05-procurement/README.md` defines the package-specific
  EOI, tender-pack, RFI/addendum, submissions, evaluation, and recommendation
  lifecycle folders.

## Domain Contracts

### Request kinds

| Kind | Target | Default form | Notes |
| --- | --- | --- | --- |
| `consultant_rfp` | Consultant discipline | Request for Fee Proposal | Existing workflow |
| `contractor_eoi` | Head contractor / builder | Expression of Interest | Existing workflow, unpriced |
| `trade_rft` | Head contractor, trade, specialist, supplier | Request for Tender | Full tender conditions and returnables |
| `trade_rfq` | Defined trade, service, or supply package | Request for Quotation | Concise conditions; full price/scope controls retained |

### Request lifecycle

```text
draft -> ready_for_issue -> issued -> closed
   \                            \
    +-----------> cancelled <---+
```

- `draft`: a working artefact exists or is being prepared.
- `ready_for_issue`: all blocking issue decisions are resolved.
- `issued`: a user records that external issue occurred, with an issue timestamp.
- `closed`: the response period is closed; responses remain editable only by
  adding revisions or correcting register metadata with an audit event.
- `cancelled`: request was abandoned without deleting its audit history.

No system transition sends a document externally.

### Recipient and response lifecycle

- Recipient outcomes: `invited`, `received`, `declined`, `withdrawn`,
  `no_response`.
- A recipient may have multiple immutable response revisions.
- One response revision may contain multiple files.
- One revision is current; superseding it never deletes prior revisions.
- Late is derived when `received_at > request.close_at`.
- Award/engagement belongs to later evaluation/contract workflows and is not a
  receipt-register state.

### Blocking issue decisions

Each request stores independently revisioned decisions for:

1. request form and package identity;
2. delivery basis (`supply_only`, `install_only`, `supply_install`,
   `design_supply_install`, or package-approved equivalent);
3. scope and issued-document baseline;
4. pricing breakdown and allowance treatment;
5. tender close, required-on-site date, and programme assumptions; and
6. contract basis, design responsibility, and material departures process.

The catalogue may provide a suggested default. A suggestion is not a locked user
decision. Missing non-blocking values render as TBC.

### Workspace paths

- Consultant paths remain unchanged under `02-consultant/`.
- Existing EOI paths remain unchanged; no migration rewrites old storage keys.
- New trade paths use:

```text
05-procurement/<canonical package name>/02-tender-pack/
  <package_slug>_<rft|rfq>_vNN.draft.md

05-procurement/<canonical package name>/04-submissions/<respondent>/
  <uploaded response files>
```

All paths pass through existing storage-key and traversal/path validation.

## Stage 1 — Governed Trade-Package Catalogue

**Outcome:** Clerk can resolve common and custom trade packages deterministically
without importing TCM taxonomy or hard-coding the catalogue into workflow code.

### Files

- Create `data/procurement/trade_packages.yaml`.
- Create `data/procurement/README.md`.
- Create `data/procurement/tools/validate.py`.
- Create `backend/app/sitewise/trade_packages.py`.
- Create `backend/tests/sitewise/test_trade_packages.py`.
- Add a data-validator test or CI invocation beside the existing tender seed
  validation pattern.

### Catalogue schema

Every entry carries:

- stable `code` and `name`;
- chronological `sequence` and `family`;
- unique normalised `aliases`;
- applicable building classes, work types, and optional work-scope signals;
- supported delivery modes and recommended default;
- baseline scope prompts and interface prompts;
- default price-breakdown rows;
- default non-price returnables;
- optional requirements for design, shop drawings, samples, testing,
  commissioning, warranties, as-builts, and O&M information; and
- active/version metadata.

Seed at least the ten chronological families approved in the PRD, with enough
entries to cover representative early works, civil, structure, envelope,
services, fitout, finishes, FF&E, specialist, and external works packages.

### Backend interface

Expose a narrow read-only interface:

- resolve a package from canonical code, name, or alias;
- list packages in construction sequence;
- filter suggestions for a project profile without declaring other packages
  unsupported;
- return a generic custom-package profile for an unknown non-empty target; and
- distinguish a catalogued profile from a custom profile.

Do not add database tables for catalogue data in this stage. Runtime read of a
validated, bounded YAML file is sufficient.

### Tests

- Codes are unique and stable-format.
- Normalised aliases are globally unambiguous.
- Sequences are ordered and families are recognised.
- Delivery modes and price rows are non-empty and valid.
- Applicability filters suggestions but does not block explicit package choice.
- Common aliases resolve to one lineage.
- A custom specialist name produces a safe generic profile.
- Blank package names are rejected at the boundary.

### Gate

`data/procurement/tools/validate.py` passes and representative package-resolution
tests are green before generation work begins.

## Stage 2 — Procurement Register Domain and Migration

**Outcome:** Requests, decisions, recipients, response revisions, and files have
a durable project-scoped source of truth independent of draft filenames and TCM.

### Files

- Create focused SQLAlchemy models under `backend/app/database/` for:
  - procurement requests;
  - request decisions;
  - recipients;
  - response revisions; and
  - response-file links.
- Register the models in the database model import surface.
- Create one reviewed Alembic migration with constraints, indexes, RLS, grants,
  and policies.
- Create `backend/app/procurement/__init__.py`.
- Create `backend/app/procurement/schemas.py`.
- Create `backend/app/procurement/register.py` as the deep service boundary.
- Add unit/integration tests under `backend/tests/procurement/`.

### Data model

`procurement_requests` includes:

- project and creator FKs;
- kind, target code/name, display package, and delivery basis;
- status and optimistic `revision`;
- current draft FK, latest workflow-run FK if useful, issue/close timestamps;
- optional instructions and request metadata; and
- created/updated timestamps.

`procurement_request_decisions` includes:

- request FK and stable decision key;
- options, selected value, source, resolved flag, rationale;
- row revision; and
- uniqueness on request plus key.

`procurement_recipients` includes request FK, organisation/contact fields,
invited timestamp, outcome, notes, revision, and timestamps.

`procurement_responses` includes request and recipient FKs, response reference,
received timestamp, response revision number, status/current marker, notes, and
timestamps.

`procurement_response_files` links a response revision to one or more existing
project `workspace_files` rows. Enforce project consistency in the service and
through the strongest practical database constraints.

### Service interface

The register service owns:

- create/get/list request;
- attach a published draft and update the current revision;
- update a request decision with optimistic concurrency;
- compute issue readiness;
- transition request status through allowed edges;
- add/update recipients;
- record a response revision;
- attach existing workspace files;
- compute invited/received/late rollups; and
- reject cross-project object composition.

Routes and MCP tools delegate to this service. They must not reimplement state
transitions or counts.

### Tests

- Schema constraints and FK targets.
- Owner A cannot read or mutate Owner B’s requests or files.
- Invalid lifecycle transitions fail with domain errors.
- A request cannot become ready while blocking decisions are unresolved.
- Optimistic decision/request updates reject stale revisions.
- Later response revisions supersede without deleting prior data.
- Late is deterministic from timestamps.
- Rollups count recipients and current responses correctly.
- Response files must belong to the same project.
- RLS migration checks follow existing project-owned table tests.

### Gate

Migration upgrade tests and procurement service tests pass before API or UI work.

## Stage 3 — Shared Procurement Renderer Seam

**Outcome:** Consultant RFP and new trade requests use the same stable project
summary, citation, document-register, and formatting atoms without changing
existing consultant output.

### Files

- Create `backend/app/sitewise/procurement_renderer.py` for genuinely shared
  deterministic atoms.
- Modify `backend/app/sitewise/rfp_renderer.py` to delegate to those atoms.
- Modify `backend/app/workflows/procurement_request.py` only where an adapter
  hook is required for a package-specific path or extra provenance.
- Update focused renderer and procurement-engine tests.
- Run all existing consultant RFP and contractor EOI fixtures unmodified.

### Shared atoms

Extract only interfaces with at least the existing and new caller:

- procurement project-summary rendering using the existing PMP summary table;
- stable citation-index creation from project evidence;
- information-to-review/document schedule table;
- safe table-cell formatting and natural document-number ordering; and
- optional common issue/submission boilerplate where wording is truly identical.

Keep consultant fee-stage language inside the RFP renderer. Keep EOI wording
inside the EOI adapter. Do not create a configurable mega-template.

### Procurement engine hooks

Add the smallest adapter hook needed for:

- package-specific workspace paths whose folder contains the target name; and
- request-specific provenance such as procurement request ID and request kind.

Default behaviour must reproduce current consultant and EOI paths byte-for-byte.

### Tests

- Existing consultant golden fixtures remain byte-identical.
- Existing contractor EOI tests remain unchanged and green.
- Shared summary output is identical for the same project/evidence inputs.
- Default workspace-path behaviour remains unchanged.
- A test adapter can override the path and provenance without bypassing storage
  sync or draft versioning.

### Gate

No RFP or EOI output drift. This is a refactor gate, not a feature gate.

## Stage 4 — Trade RFT/RFQ Generation

**Outcome:** One backend interface generates a validated, evidence-grounded
trade RFT or RFQ and publishes it as a normal Clerk draft artefact.

### Files

- Create `backend/app/workflows/trade_procurement.py`.
- Create `backend/app/sitewise/trade_request_renderer.py`.
- Create `backend/app/workflows/trade_request_narrative.py`.
- Create `backend/app/workflows/trade_request_narrative_instructions.md`.
- Create `backend/app/sitewise/trade_request_evidence_validation.py`.
- Add workflow, renderer, evidence, and golden-fixture tests under
  `backend/tests/workflows/` and `backend/tests/sitewise/`.

### Adapter behaviour

The trade adapter:

- validates `rft` versus `rfq` and resolves the package profile;
- queries active-project brief, scope, drawing/specification, approvals,
  programme, Project Plan, Cost Plan, design-responsibility, and prior package
  evidence as applicable;
- consults platform procurement, construction-sequencing, contract,
  building-class, and trade-interface guidance;
- derives no project fact from platform guidance;
- renders the approved Project Summary first;
- lists the evidence documents proposed for issue;
- tailors scope and interfaces within the catalogue/evidence boundary;
- emits the package-specific blank price schedule and returnables;
- records assumptions and missing issue inputs in provenance;
- writes the package-specific workspace path; and
- attaches the resulting draft to the procurement request.

RFT includes full conditions, RFI/addendum process, tender validity, departures,
returnables, and evaluation context. RFQ retains project, package, scope,
documents, programme, price breakdown, exclusions, qualifications, validity,
and submission controls while omitting unnecessary formal sections.

### Hybrid compiler

The deterministic renderer owns headings, tables, catalogue lines, price rows,
submission controls, and placeholders. The bounded narrative owns only:

- short project/package background;
- project-specific scope tailoring and interfaces; and
- programme/lead-time context.

The narrative receives assigned citation tokens beside evidence snippets.
Validation rejects:

- unknown citation tokens;
- uncited project-specific claims when evidence exists;
- missing scope/price/returnable sections;
- calculated or invented tender values;
- a custom-package scope that exceeds user instructions and cited evidence; and
- RFT/RFQ terminology mismatch.

Use the existing bounded retry and upstream-error handling pattern.

### Tests

- Civil/earthworks RFT.
- Structural-steel supply-and-install RFT.
- Electrical/services RFT with testing/commissioning returnables.
- Joinery or kitchen RFT with samples/shop-drawing requirements.
- Windows supply-only RFQ with lead time and unit/option pricing.
- Custom specialist package that remains generic and flags scope gaps.
- Missing evidence creates explicit issue gaps, not fabricated facts.
- Citation failure retries then succeeds; repeated failure is bounded.
- Price schedules contain blank/TBC cells only and no model-derived totals.
- Workspace path, workflow type, title, provenance, storage export, and draft
  attachment are correct.

### Gate

All six representative outputs pass fixtures and a construction-professional
red-pen review before chat/UI exposure.

## Stage 5 — Durable Workflow, API, MCP, and Chat Routing

**Outcome:** UI and chat can start, observe, cancel, and open trade request runs
through the same durable workflow contract as Project Plan, Cost Plan, RFP, and
EOI.

### Backend workflow files

- Modify `backend/app/projects/workflow_capabilities.py`.
- Modify `backend/app/workflows/runs.py`.
- Modify `backend/app/workflows/worker.py`.
- Modify `backend/app/api/projects.py`.
- Modify `backend/app/mcp_bridge/server.py`.
- Modify the MCP/direct-tool allowlists used by the selected agent runtime.
- Modify `backend/app/agent/turn_context.py` and
  `backend/app/agent/workspace_instructions.py`.
- Add API, durable-run, MCP, turn-context, and chat-acceptance tests.

### Capability

Add `trade_procurement` as a core capability requiring confirmed building class,
work type, and state. It must not reuse Tender Comparison’s Class 1/state
coverage restriction. Missing profile values yield `needs_input`; a named custom
trade is not `unsupported` merely because it is absent from suggestions.

### Durable workflow

Add base run type `trade_procurement` with parameters:

- request ID when an existing hub draft is being generated;
- request kind (`rft` or `rfq`);
- package code/name;
- delivery basis;
- optional max-length/instructions; and
- the existing frozen snapshot, profile revision, decision-set revision,
  idempotency, thread, and turn inputs.

The start service creates or reuses the request idempotently, then queues the
run. The worker calls the Stage 4 generator, attaches the draft, and publishes
the normal workflow result and artefact event. Do not add a legacy synchronous
trade-drafting tool.

### API

Add project-owned JSON endpoints for:

- list/create/get procurement request;
- read/update request decisions;
- start a trade request run;
- mark ready, issued, closed, or cancelled through validated transitions; and
- read current register rollups.

Use the existing API client response conventions, entitlement seam, and
project-owner checks.

### MCP

Add `start_trade_procurement` as the durable action tool. It authorizes the
project at the tool layer, validates package/kind, delegates to the same start
service as HTTP, and returns the normal run metadata.

Chat routing:

- consultant fee proposal, consultant services, and named design consultant ->
  `start_consultant_procurement`;
- RFT, invite to tender, trade tender, contractor tender ->
  `start_trade_procurement(kind=rft)`;
- RFQ, quotation request, quote this defined package ->
  `start_trade_procurement(kind=rfq)`;
- head-contractor EOI or shortlist -> `start_contractor_eoi`;
- compare, evaluate, normalise, recommend, select, award, or analyse received
  tenders -> Tender Comparison or an explicit unsupported/downstream response,
  never a new request.

“Request for services” routes from the named target. If the target does not
establish consultant versus trade/service, ask one short clarification and do
not queue a run.

### Tests

- Capability supported across representative residential/commercial/industrial
  profiles and needs input only for missing required context.
- Durable-run idempotency and worker dispatch.
- Retry, lease, cancellation, and result publication.
- HTTP ownership, entitlement, stale snapshot, and validation failures.
- MCP tool authorization and cross-project rejection.
- Status and artefact events use the existing SSE contract.
- Positive chat phrases route correctly.
- Negative compare/evaluate/award phrases never queue procurement drafting.

### Gate

A real chat turn can queue a structural-steel RFT, show progress, and open the
completed artefact without a synchronous tool fallback.

## Stage 6 — RFP / RFT Hub and Navigation Split

**Outcome:** Users can browse and create procurement requests from a dedicated
hub while Tender Comparison remains a separate adjacent workflow.

### Files

- Modify `frontend/src/components/project/workflow/workflowTiles.ts`.
- Modify `frontend/src/components/project/workflow/workflowRouting.ts`.
- Modify `frontend/src/pages/ProjectCockpitPage.tsx`.
- Modify `frontend/src/App.tsx`.
- Create `frontend/src/components/project/procurement/` components for the route
  frame, request list, request detail, creation form, package picker, issue
  readiness, and status controls.
- Create `frontend/src/lib/types/procurement.ts`.
- Create `frontend/src/lib/queries/procurement.ts`.
- Extend `frontend/src/lib/api.ts` through its existing typed API surface.
- Add Vitest render and routing tests.

### Navigation

Replace the overloaded internal `procurement` tile identity with two explicit
IDs:

- `procurement-requests` -> label `RFP / RFT` -> `/requests`;
- `tender-comparison` -> label `Tender Comparison` -> existing `/tender`.

Update workspace routing:

- consultant procurement, contractor EOI, and RFT slugs route to requests;
- tender evaluation/recommendation slugs route to Tender Comparison.

Preserve existing `/tender` URLs and browser history. Generalise cockpit helpers
that currently assume the only nested route is Tender Comparison so selecting a
file, draft, request, or comparison leaves/keeps the correct nested route.

### Hub

The request list shows:

- target/package;
- request kind;
- current draft version/status;
- issue/close dates;
- recipient count;
- received count; and
- last updated time.

The creation form provides:

- consultant versus trade request choice;
- RFP/RFT/RFQ selection constrained by target category;
- chronological grouped package picker plus custom target;
- delivery basis;
- close/required dates when known; and
- concise additional instructions.

Consultant creation delegates to the current consultant run. Trade creation
delegates to the new run. EOI remains available for head-contractor shortlisting.

The detail view shows issue decisions, current draft/open action, recipients,
responses, and activity. Reuse current buttons, tables, loading patterns,
workflow progress strip, and draft review rather than adding a new design system.

### Request decisions

Create a request-scoped control visually consistent with `DecisionControl`, but
backed by request decision endpoints. It displays suggestion/evidence status,
uses optimistic revisions, and recomputes ready-for-issue after each save.

### Tests

- Exact left-nav order and labels.
- Requests and Tender Comparison open distinct routes.
- Existing tender deep links remain valid.
- Package picker groups/sorts chronologically and resolves aliases/custom input.
- Consultant/trade forms call the correct endpoint.
- Workflow progress, failure, cancellation, and completed artefact states.
- Decision update conflict and readiness refresh.
- Empty, loading, error, and populated request lists.

### Gate

Manual navigation check passes on desktop widths supported by the cockpit, with
back/forward navigation correct across requests, tender comparison, files, and
chat artefact links.

## Stage 7 — Recipients and Received-Response Register

**Outcome:** Users can record who was invited and which proposal/tender/quote
files were received, including revisions.

### Backend files

- Add recipient and response endpoints to the project API or a focused
  procurement router mounted by the main app.
- Extend procurement service and schemas only where Stage 2 did not already
  expose the required methods.
- Reuse project upload, storage, workspace-file, ingestion-queue, and path
  services.
- Add backend tests under `backend/tests/procurement/`.

### Frontend files

- Add recipient and response controls under the procurement component folder.
- Extend procurement queries/types.
- Reuse repository upload progress and API error patterns where practical;
  extract shared upload code only if doing so produces a clear, tested interface.
- Add Vitest tests for add/edit/receive/revise/link flows.

### Behaviour

- Add a recipient before or after issue.
- Record invited timestamp and contact details without sending anything.
- Record declined/withdrawn/no-response outcomes with notes.
- “Add response” supports:
  1. uploading one or more new files directly to the canonical submissions
     folder; or
  2. selecting existing project workspace files.
- New uploads go through the existing storage and core ingestion pipeline so
  they remain normal project documents available to retrieval.
- Register the response only after file persistence succeeds. Surface partial
  upload failures explicitly; do not silently claim a complete response.
- Adding a later response creates a new immutable revision and marks it current.
- Display late status from the close/received timestamps.
- Never infer and commit a request/recipient match solely from filename or LLM
  classification. Suggestions require user confirmation.

### Tests

- Recipient CRUD and outcome transitions with owner/entitlement checks.
- Direct upload uses canonical package/respondent path and queues ingestion.
- Existing-file attachment checks project ownership.
- Multi-file response is one revision.
- Revised response retains prior revision/files.
- Partial failure returns an accurate result.
- Received and late rollups update in the UI.
- No automatic issue, email, award, or comparison side effect occurs.

### Gate

For one RFT, record four recipients, receive three multi-file submissions (one
late and one revised), and confirm the hub reports the correct counts and audit
history.

## Stage 8 — Document Schedule Artefact Rows

**Outcome:** Existing RFPs/EOIs and new RFT/RFQs are visible and openable from
both repository views without changing their evidentiary classification.

### Backend files

- Generalise the consultant-only latest-draft-summary query in
  `backend/app/database/draft_artifacts.py` into a procurement-aware query or a
  safe general latest-by-prefix interface.
- Modify cockpit bootstrap and workspace-tree assembly in
  `backend/app/api/projects.py` to include consultant RFP, contractor EOI, trade
  RFT, and trade RFQ latest summaries and workspace self-heal.
- Extend bootstrap/workspace API tests.

### Frontend files

- Modify `frontend/src/components/project/DocumentRepositoryPanel.tsx`.
- Modify its tests.
- Modify `frontend/src/pages/ProjectCockpitPage.tsx` and project types as needed.
- Extend workspace/draft routing helpers and tests.

### Schedule row contract

Introduce a discriminated presentation row:

- `source`: existing evidence preview, source selection, usage marks, and source
  deletion behaviour;
- `artefact`: draft ID, workflow type, title, version, workspace path, category,
  status, and updated time.

Schedule rows include latest procurement artefacts. Clicking:

- a source row follows the existing source-document path;
- an artefact row opens `DraftReviewPanel` using its draft identity/path.

Artefact rows:

- are labelled RFP, EOI, RFT, or RFQ;
- cannot enter source multi-select or delete controls;
- do not become `selectedRepositoryEvidence` for Tender Comparison;
- update from project artefact events; and
- remain visible even when no `source_document_id` exists.

Historical draft versions remain workspace files in tree mode. Schedule mode
shows only the current request revision to avoid duplicate clutter.

### Tests

- Existing consultant RFP appears in schedule and tree.
- Existing contractor EOI opens as a draft.
- New RFT/RFQ rows render correct category/version.
- Artefact click opens Markdown review in the main panel.
- Source click and shift/control selection remain unchanged.
- Artefacts never enter source deletion or tender document selection.
- Live artefact events add/update the schedule row.
- Workspace self-heal is invoked for all procurement draft families.

### Gate

The same latest RFP/RFT artefact can be opened from chat, hub, tree, and schedule,
and every path resolves to the same draft revision.

## Stage 9 — Legacy Backfill, Acceptance, and Rollout

**Outcome:** Existing procurement history is represented without rewriting
artefacts, and the full feature is proven before individual stages are marked
ready for autonomous implementation.

### Backfill

- Create an idempotent application backfill command/script rather than embedding
  filename parsing into normal request reads.
- Scan existing draft artefacts with consultant-procurement and contractor-EOI
  workflow families.
- Group by project and workflow lineage.
- Create one procurement request per lineage when absent.
- Derive request kind and target from trusted provenance first, then canonical
  workflow suffix as a fallback.
- Attach the latest draft as current while preserving every existing path,
  version, status, and storage key.
- Do not invent recipients, issue dates, or responses.
- Record counts and conflicts; rerunning produces zero duplicates.

### Automated verification

Backend, from `backend/`:

```powershell
uv run pytest tests/procurement tests/workflows tests/mcp_bridge tests/agent -q
uv run pytest tests/test_project_cockpit_bootstrap.py tests/test_project_draft_versioning.py -q
uv run ruff check app tests/procurement
```

Run the existing consultant RFP and contractor EOI suites explicitly even if
included above. Run the broader backend suite before merge.

Frontend, from `frontend/`:

```powershell
pnpm test
pnpm tsc --noEmit
pnpm lint
```

Run the procurement, repository, workspace-routing, workflow-routing, and
ProjectCockpitPage tests explicitly before the full frontend suite.

### Scripted acceptance scenarios

1. **Consultant regression:** chat creates a structural-engineer fee proposal;
   it appears in hub, tree, schedule, and draft review with current citations.
2. **Early trade RFT:** chat creates a structural-steel supply-and-install RFT;
   request status is draft until blocking decisions are resolved.
3. **Supply RFQ:** hub creates a windows supply-only RFQ with lead-time, options,
   unit pricing, and exclusions but without unnecessary RFT formality.
4. **Custom package:** chat creates a specialist aquarium-glazing RFT; output
   states missing scope rather than inventing specialist requirements.
5. **Receipt audit:** four invitees, three responses, one late, one revised; all
   files open and counts/history are correct.
6. **Negative intent:** “compare the three roofing quotes” does not create an
   RFT/RFQ and remains routed to Tender Comparison or its governed capability
   response.
7. **Tenancy:** a second project/user cannot access request, recipient, response,
   draft, or file identifiers from the first.
8. **Legacy:** pre-feature RFP and EOI drafts are backfilled once and open from
   every intended surface.

### Manual quality gate

Review at least one civil, structural, services, envelope, finishes, and
supply-only output against real project evidence. Confirm:

- concise Project Summary;
- correct package identity and interfaces;
- correct document revisions;
- useful, package-specific price schedule;
- no unsupported project fact;
- no model arithmetic;
- visible issue decisions/TBC gaps; and
- clear distinction between draft preparation and external issue.

### Rollout

- Apply schema migration.
- Deploy code with the hub visible only once endpoints and backfill are ready;
  do not add a speculative feature flag unless the deployment sequence requires
  one of the existing phase gates.
- Run the idempotent backfill and retain its report.
- Complete smoke scenarios on a non-production project.
- Enable the nav item and update product/runbook documentation.
- Monitor workflow failures, register conflicts, and unmatched legacy artefacts.

## Cross-Cutting Security and Quality Rules

- Every API/MCP mutation performs project authorization at its boundary.
- Turn-token project binding remains mandatory for agent tools.
- Response files are commercially sensitive project evidence in private storage.
- File paths are canonicalised and traversal-safe.
- Source documents and generated artefacts keep distinct identities.
- External actions are never inferred from a draft/status update.
- Request and decision updates use optimistic concurrency.
- Workflow starts are idempotent and snapshot-bound.
- Project evidence outranks platform guidance.
- Platform guidance is labelled guidance in provenance.
- Custom package fallback cannot add ungrounded specialist scope.
- Existing consultant RFP and EOI behaviour is regression-protected.
- No new Clerk core imports from `backend/tender/`.
- No dependency is added unless it satisfies the repository dependency policy.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| “All trades” becomes an unmaintainable hard-coded list | Governed data catalogue plus custom fallback; keep workflow code catalogue-agnostic |
| Package aliases create duplicate draft lineages | Globally validate normalised aliases and canonicalise before request creation |
| Generic model knowledge invents trade scope | Catalogue/evidence boundary, citation validation, explicit gap output, custom-package constraints |
| RFT drafting is confused with Tender Comparison | Separate nav IDs/routes/tools plus negative intent tests |
| Request decisions collide across packages | Request-scoped decision rows, not global ProjectDecision IDs |
| Artefacts are ingested as evidence to appear in schedule | Merge presentation rows; keep draft artefacts authoritative |
| Received files are attached to the wrong request | Explicit user confirmation and same-project validation; inference remains a suggestion only |
| Existing RFP/EOI data disappears from the new surface | Idempotent provenance-first backfill and compatibility tests |
| Refactor changes consultant output | Byte-identical golden gate before new generator work |
| New hub bloats ProjectCockpitPage | Nested route and focused procurement component/query modules |
| Formal RFT language implies automatic legal issue | Draft watermark/status, blocking readiness, manual issue record, explicit out-of-scope boundary |

## Proposed Issue Split After Plan Sign-Off

| Issue | Slice | Depends on |
| --- | --- | --- |
| PRQ-001 | Catalogue schema, seed, loader, validator | none |
| PRQ-002 | Procurement register models, migration, RLS | none |
| PRQ-003 | Procurement register deep service | PRQ-002 |
| PRQ-004 | Shared renderer seam with no RFP/EOI drift | none |
| PRQ-005 | Trade RFT/RFQ renderer and hybrid compiler | PRQ-001, PRQ-004 |
| PRQ-006 | Trade request artefact integration with register | PRQ-003, PRQ-005 |
| PRQ-007 | Durable workflow, capability, API, and worker | PRQ-006 |
| PRQ-008 | MCP tool and chat routing | PRQ-007 |
| PRQ-009 | Requests nav split, route, list, and creation | PRQ-007 |
| PRQ-010 | Request decisions and issue-readiness UI | PRQ-003, PRQ-009 |
| PRQ-011 | Recipient and response backend | PRQ-003 |
| PRQ-012 | Recipient/response UI and upload/link flow | PRQ-009, PRQ-011 |
| PRQ-013 | Repository schedule artefact rows | PRQ-006, PRQ-009 |
| PRQ-014 | Legacy backfill and rollout runbook | PRQ-002, PRQ-013 |
| PRQ-015 | Scripted acceptance and red-pen quality gate | all prior |

Do not publish these as implementation issues until the PRD and this plan have
been reviewed. When published, mark independently implementable code slices
`ready-for-agent`; keep the construction-professional red-pen and production
rollout gates `ready-for-human`.

## Definition of Done

- Consultant RFP, contractor EOI, trade RFT, and trade RFQ are reachable from
  one RFP / RFT hub.
- Chat reliably distinguishes request creation from tender comparison.
- Representative packages across the construction sequence generate concise,
  cited, validated, package-specific drafts.
- Custom packages work without fabricated scope.
- Price schedules are useful and deterministic.
- Blocking issue decisions govern ready-for-issue state.
- Recipients and response revisions form an auditable register with file links.
- Existing procurement artefacts are backfilled without duplication.
- Latest procurement drafts appear and open in schedule and tree views.
- Generated artefacts remain distinct from project evidence.
- Project authorization, RLS, path safety, idempotency, cancellation, and
  optimistic concurrency tests pass.
- Existing consultant RFP, contractor EOI, Tender Comparison, Project Plan, Cost
  Plan, chat, and repository behaviours remain green.
- Manual quality and end-to-end acceptance gates are recorded before rollout.
