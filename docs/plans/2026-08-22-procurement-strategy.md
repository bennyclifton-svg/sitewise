# Procurement Strategy Implementation Plan

**Date:** 2026-08-22  
**Status:** Approved interaction direction; ready for implementation  
**Surface:** Project cockpit → Procurement  
**Ownership:** SiteWise core (`backend/app/` and `frontend/src/`), not Tender Comparison

## Goal

Add a durable Procurement Strategy register to the existing Procurement panel.
The register uses the same project discipline vocabulary as the PMP and the RFT
workflows, lets a user nominate three tenderers by default (with an optional
fourth column), records package status and notes, and can be read and changed by
Pi through authorised tools.

The feature is successful when a user can:

1. Open Procurement and retain the current Discipline → Generate RFT → Update
   RFT workflow.
2. Click **Strategy** beside those controls and see the project discipline
   register instead of the current RFT preview.
3. Add and edit tenderers, status, notes, order, and locked state.
4. Ask Pi to research named disciplines and populate sourced candidates.
5. Generate or update an RFT against the same discipline identity used by the
   Strategy and PMP.

## Confirmed interaction

The Procurement header remains one toolbar:

```text
[ Discipline ▾ ] [ Generate RFT ] [ Update RFT ] [ Strategy ]     [download] [copy]
```

- **Strategy** is a button in the existing toolbar, not a fourth request type
  and not a separate cockpit route.
- Activating Strategy replaces the RFT preview with the register. The Strategy
  button shows selected state. Activating it again returns to the current RFT.
- RFT download/copy actions are hidden while Strategy is active because they
  act on the current RFT, not the register.
- Generate and Update remain visible. If invoked from Strategy they return the
  surface to the RFT view while the chat workflow starts.
- The first column is named **Discipline**. “Discipline” is the user-facing
  umbrella term for consultant disciplines, contractor trade packages, and
  supplier packages.
- The table initially shows **Tenderer 1**, **Tenderer 2**, and **Tenderer 3**.
  A `+ Add Tenderer 4` header action adds and persists the fourth column for the
  project strategy.
- Remaining columns are **Status**, **Notes**, and the row actions menu.
- Row actions are: Edit with AI, Add row above, Add row below, Lock/Unlock, and
  Delete.

## Current-state finding: there is no master discipline list yet

The current application has several overlapping vocabularies:

- `frontend/src/lib/procurement-disciplines.ts` contains frontend consultant and
  trade fallbacks and guesses request kind from a label.
- `backend/app/workflows/consultant_procurement.py` owns consultant workflow
  profiles and aliases.
- `backend/app/workflows/trade_procurement.py` owns trade/supplier profiles and
  aliases.
- `data/taxonomy/work-scopes.json` names consultants required by work scope.
- `backend/ingest/document_metadata.py` owns document-filing discipline labels.
- The PMP renderer derives its consultant roster separately from work scope,
  typical-house rules, and shared consultant facts.

Procurement Strategy must not add another copy. The first implementation slice
therefore creates a canonical catalogue with stable discipline codes. Existing
workflows may continue to own their scope prose and deliverable templates, but
they must point to catalogue codes rather than define identity independently.

## Domain model

### Canonical discipline catalogue

Add `data/taxonomy/disciplines.json` and load it through
`backend/app/sitewise/discipline_catalog.py`.

Each entry contains:

```json
{
  "code": "consultant.structural",
  "label": "Structural",
  "participant_type": "consultant",
  "request_kind": "consultant_rfp",
  "aliases": ["Structural engineer", "Structural engineering"],
  "workspace_slug": "structural-engineer",
  "pmp_label": "Structural"
}
```

`participant_type` is one of `consultant`, `trade`, or `supplier`.
`request_kind` is one of the existing Clerk request kinds. Labels can overlap
only when the stable code is different; aliases must resolve unambiguously.

Representative identities:

```text
consultant.structural     → Structural             → consultant_rfp
consultant.architect      → Architecture           → consultant_rfp
consultant.civil          → Civil                  → consultant_rfp
trade.electrical          → Electrical Services    → trade_rft
trade.structural_steel    → Structural Steel       → trade_rft
supplier.windows_glazing  → Windows and Glazing    → trade_rfq
```

The catalogue loader must provide:

- lookup by stable code;
- strict alias-to-code resolution;
- labels for user-facing rendering;
- filtering by participant type;
- validation that aliases are unique and workflow profile keys resolve;
- project-specific discipline derivation.

Add `required_project_disciplines(project)` as the single resolver used by PMP
and Procurement. It combines, in stable order:

1. work-scope-required consultant and trade codes;
2. typical-project rules such as the house starter roster;
3. shared consultant facts and existing appointments;
4. existing procurement requests;
5. user-created custom strategy rows.

The resolver returns source metadata so the UI and refresh logic know why a
discipline is present. It must deduplicate by stable code, never by display
label alone.

### Persistence

Add three SiteWise-core models.

#### `procurement_strategies`

- `id`
- `project_id` — unique FK to `projects`, cascade delete
- `revision` — optimistic-concurrency revision, starts at 1
- `tenderer_column_count` — `3 | 4`, default 3
- `source_fingerprint` — fingerprint of the project discipline inputs used by
  the last refresh
- timestamps

#### `procurement_strategy_rows`

- `id`
- `strategy_id` — FK, cascade delete
- `discipline_code` — nullable only for a user-created custom discipline
- `discipline_label` — stored display snapshot for custom rows and history
- `participant_type` — `consultant | trade | supplier`
- `request_kind` — existing procurement request kind
- `status`
- `notes`
- `display_order`
- `origin` — `derived | existing_request | manual`
- `locked`
- timestamps

Derived rows are unique on `(strategy_id, discipline_code)`. Manual rows have a
generated row ID and can later be reconciled to a catalogue code explicitly;
fuzzy matching must not silently merge them.

#### `procurement_strategy_candidates`

- `id`
- `strategy_row_id` — FK, cascade delete
- `slot` — integer `1..4`, unique per row
- `company_name`
- `website_url`
- `location_text`
- `source_url`
- `source_title`
- `researched_at`
- timestamps

The UI is column-shaped, but candidates remain row records so adding Tenderer 4
does not require a schema change. Candidate sources are external research
provenance, not project evidence.

Add nullable `discipline_code` and `strategy_row_id` to
`procurement_requests`. New requests must use them. Existing requests receive a
deterministic best-effort backfill from exact catalogue labels/aliases; custom
or ambiguous legacy targets remain unlinked for manual review.

### Status contract

Use a small package-level status vocabulary:

```text
not_started
researching
shortlisting
request_drafted
issued
responses_received
evaluating
awarded
cancelled
```

The browser renders friendly labels. Early statuses are editable. Linked
procurement lifecycle events advance status as follows:

- generated draft attached → `request_drafted`
- issue email sent / request issued → `issued`
- at least one linked submission → `responses_received`
- explicit evaluation start → `evaluating`
- consultant appointment or explicit user award → `awarded`
- cancelled request with no active replacement → `cancelled`

Locking protects discipline identity, tenderers, notes, order, deletion, and
automated roster refresh. It does not prevent server-owned lifecycle status
from reflecting an issued request or received submission.

## Service and API contracts

Create `backend/app/procurement/strategy.py` as the domain service. HTTP routes
and MCP tools call the same service; neither writes tables directly.

### Domain operations

```python
async def ensure_procurement_strategy(...)
async def get_procurement_strategy(...)
async def refresh_procurement_strategy(...)
async def apply_procurement_strategy_operations(...)
async def link_request_to_strategy_row(...)
async def advance_strategy_status(...)
```

`ensure` is idempotent and is called only from an explicit user action such as
clicking Strategy. A GET route must not create database state.

`refresh` compares the live required discipline set to persisted rows:

- add newly required disciplines;
- keep manual rows;
- keep tenderers and notes;
- leave locked rows untouched;
- flag no-longer-required derived rows in the response instead of deleting
  them;
- never merge custom rows through fuzzy matching.

### Operation envelope

Use one typed batch contract for browser and agent writes:

```text
ADD_ROW
UPDATE_ROW
MOVE_ROW
DELETE_ROW
LOCK_ROW
UNLOCK_ROW
UPSERT_CANDIDATE
CLEAR_CANDIDATE
SET_TENDERER_COLUMN_COUNT
```

Every batch includes `expected_revision`; success increments the strategy
revision once. Limit batches to 50 operations. Locked-row violations and stale
revisions return conflict responses, not silent rebases.

### REST surface

Under the existing project router:

```text
GET  /projects/{project_id}/disciplines
GET  /projects/{project_id}/procurement-strategy
POST /projects/{project_id}/procurement-strategy/ensure
POST /projects/{project_id}/procurement-strategy/refresh
POST /projects/{project_id}/procurement-strategy/operations
```

All routes enforce project ownership. Mutations use the existing entitlement
seam. Responses return the complete strategy snapshot because the expected
table size is small and this keeps optimistic rollback simple.

## Implementation slices

### Slice 1 — Establish the master discipline catalogue

**Files**

- Add `data/taxonomy/disciplines.json`.
- Add `backend/app/sitewise/discipline_catalog.py`.
- Update `backend/app/sitewise/taxonomy.py` and
  `data/taxonomy/work-scopes.json` to reference discipline codes.
- Update PMP consultant-roster derivation to call
  `required_project_disciplines(project)` and filter consultant entries.
- Update consultant/trade workflow profile maps to declare a catalogue code.
- Update ingest discipline mappings to resolve through the catalogue.
- Add `backend/tests/sitewise/test_discipline_catalog.py`.

**Rules**

- Workflow scope prose remains in the workflow modules; identity and aliases do
  not.
- Remove frontend fallback arrays after the API consumer lands.
- Add a validation test that every work-scope, workflow-profile, and ingest
  mapping code exists and every alias is unambiguous.
- Do not import from `backend/tender/`; TCM keeps its project-specific quote
  taxonomy separate.

**Commit:** `refactor: establish the SiteWise discipline catalogue`

### Slice 2 — Persist the strategy register

**Files**

- Add `backend/app/database/procurement_strategy.py`.
- Import models from `backend/app/database/models.py`.
- Add Alembic migration `058_procurement_strategy.py` after confirming the live
  head remains `057_procurement_submissions`.
- Add `backend/app/procurement/strategy.py`.
- Add schemas to `backend/app/schemas/projects.py`.
- Add service tests under `backend/tests/procurement/`.

**Migration requirements**

- table checks for statuses, participant types, slots, and column count;
- unique project strategy and unique row slot constraints;
- indexes on project, strategy row order, and discipline code;
- RLS enabled with owner policies following current procurement tables;
- nullable request linkage columns with safe legacy backfill;
- no data loss or rewriting of current procurement requests.

**Tests**

- ensure is idempotent;
- generated rows match the PMP discipline resolver;
- three columns are the default and four persists;
- refresh adds requirements without losing candidates or notes;
- locked rows survive refresh;
- manual rows are not fuzzy-merged;
- stale revisions fail;
- cross-project row IDs fail closed.

**Commit:** `feat: persist project procurement strategies`

### Slice 3 — Add the project API and frontend types

**Files**

- Add routes to `backend/app/api/projects.py`.
- Add API tests to `backend/tests/api/` or the existing project-route suite.
- Add strategy and discipline types to
  `frontend/src/lib/types/project.ts`.
- Add API methods to `frontend/src/lib/api.ts`.
- Add `workbenchKeys.procurementStrategy(projectId)` and prefetch support in
  `frontend/src/lib/queries/workbench.ts`.

**Behaviour**

- Clicking Strategy calls `ensure` the first time, then uses the TanStack Query
  cache.
- Subsequent opens read without a creation mutation.
- API errors preserve the current RFT view and show a concise panel-level
  error.

**Commit:** `feat: expose the procurement strategy register`

### Slice 4 — Build the Strategy grid in the existing panel

**Files**

- Add `frontend/src/components/project/ProcurementStrategyGrid.tsx`.
- Add `frontend/src/components/project/ProcurementStrategyGrid.test.tsx`.
- Update `frontend/src/components/project/ProcurementRequestPanel.tsx`.
- Update `frontend/src/components/project/ProcurementRequestPanel.test.tsx`.
- Reuse existing button, dropdown-menu, suggestion-field, and instruction
  controls; add no UI dependency.

**Panel changes**

- Rename the current primary control from `Create RFT` to `Generate RFT`.
- Add `view: "request" | "strategy"` local state.
- Place Strategy immediately after Update RFT.
- Use selected button styling and `aria-pressed`.
- Hide RFT download/copy controls in Strategy view.
- Return to request view when Generate or Update is invoked.
- Remove request-kind guessing from `kindForTargetName`; the selected catalogue
  discipline supplies the request kind.

**Grid behaviour**

- sticky Discipline column and horizontally scrollable table body;
- three tenderer columns initially;
- `+ Add Tenderer 4` replaces itself with the persisted fourth column;
- inline company, status, and notes editing;
- Enter/blur commits, Escape cancels;
- optimistic update with rollback and conflict reload;
- Add row above/below opens a catalogue-backed discipline picker;
- lock visibly disables protected cells and destructive actions;
- Delete requires confirmation when a row contains candidates or a linked
  request;
- compact loading skeleton, empty state, error state, and narrow-width overflow;
- no extra dashboard cards or duplicated request-status summaries.

**Commit:** `feat: add Procurement Strategy to the workbench`

### Slice 5 — Connect disciplines, requests, and status

**Files**

- Update `backend/app/procurement/requests.py`.
- Update procurement workflow start/attach paths in
  `backend/app/workflows/consultant_procurement.py`,
  `backend/app/workflows/trade_procurement.py`, and shared request helpers.
- Extend procurement request schemas and frontend types with discipline and
  strategy-row identity.
- Update closed-loop issue/submission services to advance strategy status.
- Add regression coverage beside current procurement workflow and submission
  tests.

**Behaviour**

- The selected master discipline code determines consultant RFP, trade RFT, or
  supplier RFQ internally, while the toolbar remains labelled Generate RFT.
- Workflow calls accept optional `discipline_code` and `strategy_row_id` and
  validate that the row belongs to the project and matches the request kind.
- Generated drafts link to the row without label matching.
- Existing request revisions remain attached to the same row.
- Draft, issue, and submission events advance status through the domain service.
- Consultant appointment advances a linked consultant row to Awarded.
- Trade award stays a deliberate manual transition until an existing typed
  award action can supply authoritative data.

**Commit:** `feat: link procurement requests to strategy rows`

### Slice 6 — Make the register agent-addressable

**MCP tools**

```text
get_procurement_strategy
refresh_procurement_strategy
apply_procurement_strategy_operations
search_procurement_candidates
```

**Files**

- Add tools to `backend/app/mcp_bridge/server.py`.
- Add direct tools to `backend/app/agent/pi_process.py`.
- Add concise doctrine to `backend/app/agent/workspace_instructions.py` and
  `backend/app/agent/turn_context.py`.
- Add `PROCUREMENT_STRATEGY_MUTATION_SCOPE` and explicit-intent detection to
  `backend/app/agent/mutation_intent.py`.
- Add MCP/auth/prompt tests.

**Tool rules**

- Reads require project access.
- Writes require the durable turn capability and the strategy mutation scope.
- The operation tool accepts catalogue codes and row IDs returned by the read
  tool; Pi must not edit rendered Markdown or guess database identifiers.
- Every successful mutation publishes a `procurement_strategy` resource event.
  The cockpit invalidates `workbenchKeys.procurementStrategy(projectId)` when it
  receives that event.
- The row action **Edit with AI** opens the existing compact instruction UI and
  sends a human-readable anchored instruction such as:
  `Update the Structural row in Procurement Strategy: ...`.
  The unique discipline identity is resolved by the strategy read tool.

Agent examples to cover:

```text
Research three structural engineers, three architects and three civil
engineers and populate the Procurement Strategy.

Add North & Co as Tenderer 2 for Structural and change the status to
Shortlisting.

Lock the Architecture row and add Electrical below Civil.
```

**Commit:** `feat: let Pi manage Procurement Strategy`

### Slice 7 — Add sourced commercial candidate research

The existing `search_web` path must remain restricted to official Australian
government sources. Do not relax that epistemic boundary.

**Files**

- Add `backend/app/market_research/` with a procurement candidate service.
- Reuse the existing configured search-provider interface and Brave provider;
  add no runtime dependency.
- Add explicit settings in `backend/app/config.py` and examples in
  `backend/.env.example`.
- Add safe-fetch, service, and MCP tests with fake providers and no live
  network.

**Research contract**

- Search project locality first when the profile has an address, then state,
  then Australia.
- Return distinct companies with name, website, location, source title, source
  URL, and a short capability excerpt.
- Read/verify the selected company page before it can be persisted.
- Permit only public HTTPS targets; reject loopback, private/link-local IPs,
  unsafe redirects, oversized responses, and unsupported content.
- Do not scrape personal contact details or claim availability, insurance,
  registration, suitability, or “best” ranking without a supporting source.
- Store candidate provenance on the strategy candidate. Do not ingest it as
  `project_evidence` and do not present it as proof of appointment.
- A research-only request returns candidates without writing. An explicit
  “populate/add/save” request may call the strategy operation tool after the
  search.
- If commercial search is not configured, return a clear capability error and
  leave the table unchanged.

**Commit:** `feat: research sourced procurement candidates`

### Slice 8 — Integration hardening and acceptance

**Backend checks**

```powershell
cd backend
uv run ruff check .
uv run pytest tests/sitewise/test_discipline_catalog.py
uv run pytest tests/procurement
uv run pytest tests/mcp_bridge
uv run pytest tests/workflows/test_consultant_procurement.py tests/workflows/test_trade_procurement.py
uv run alembic upgrade head
```

Use narrower named tests during development; run the full backend suite before
release when the environment permits it.

**Frontend checks**

```powershell
cd frontend
pnpm typecheck
pnpm lint
pnpm vitest run src/components/project/ProcurementStrategyGrid.test.tsx src/components/project/ProcurementRequestPanel.test.tsx
```

Run one bounded visual QA pass at desktop and narrow widths, fix the resulting
batch, then confirm once. Verify both dark and light token modes if both remain
supported by the cockpit.

**Acceptance scenarios**

1. A house project opens Strategy and receives Architecture, Structural, Town
   Planning, and Civil from the same resolver used by the PMP.
2. The table starts with three tenderer columns. Add Tenderer 4, reload, and
   confirm it persists.
3. Add firms, status, and notes; reload and confirm exact values and order.
4. Lock Structural, refresh from the Project Profile, and confirm the row is
   unchanged while a newly required discipline is added.
5. Generate an RFT for Structural and confirm the request and strategy row share
   a discipline code and the row advances to Request drafted.
6. Issue the request and ingest a linked submission; confirm status advances to
   Issued then Responses received.
7. Ask Pi to add a named firm and confirm the table refreshes from the resource
   event without a page reload.
8. Ask Pi to research three firms across three disciplines; confirm distinct,
   sourced candidates are populated and labelled as external research.
9. Attempt the same mutation from another project, a stale revision, a locked
   row, and a turn without mutation scope; all fail closed.
10. Confirm existing RFT generation, update, download, copy, PMP rendering, and
    Tender Comparison tests remain green.

**Commit:** `test: harden Procurement Strategy integration`

## Explicit non-goals

- Procurement Strategy does not become a Tender Comparison table and does not
  import `backend/tender/`.
- Candidate research is not project evidence, prequalification, recommendation,
  or appointment.
- The first release does not send RFTs automatically; existing user-approved
  issue-email rules remain binding.
- The first release does not compare quotes or compute commercial rankings.
- The table is not stored as PMP Markdown and does not depend on parsing the
  latest PMP draft.
- No new frontend state library, HTTP library, or search dependency is added.

## Recommended delivery order

Implement and merge the slices in order. Slices 1–3 establish the domain and
persistence seam. Slice 4 delivers the manual Strategy register. Slice 5 closes
the existing procurement lifecycle. Slice 6 makes the table agent-addressable.
Slice 7 adds external market research last so a search-provider issue cannot
block the durable register itself.

The minimum coherent release is Slices 1–6. Slice 7 may be feature-gated by
deployment configuration, but its tool must fail explicitly rather than
silently returning model-invented firms.
