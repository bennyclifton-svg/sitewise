# SiteWise — Unified Project Context, Addressable Artefacts, Incremental Generation & High-Performance Editing
## Full Staged Implementation Plan

**Status:** Follow-up remediation in progress (F0-F1 complete; F2-F10 pending)
**Primary objectives:** Improve artefact quality, responsiveness, consistency, flexibility, maintainability and user trust.

## Verified Implementation Status

The 2026-08-10 post-implementation audit found original Stages 2, 3, 6, 9, 11
and 22 implemented and the other 20 stages partially implemented. The former
blanket completion claim and its test counts were not supported by the available
workspace. Closeout is governed by
`docs/plans/unified-project-context/01-post-implementation-follow-up.md`.

Follow-up Stage F0 is complete in the current, uncommitted workspace. It restored
the green regression baseline, made block-marker stripping reversible, preserved
valid addressable table rows through rendering and export, and documented the
internal Markdown boundary. Verification at that checkpoint:

```text
Backend default suite     1,814 passed, 0 failed, 7 skipped, 27 deselected
Frontend suite            53 files, 326 tests passed
Frontend production build passed enforced bundle budgets
Backend Ruff              passed
F0 frontend ESLint        passed
Repository-wide ESLint    3 pre-existing errors and 2 warnings remain
```

Follow-up Stage F1 is also complete in the current, uncommitted workspace. It
separates the canonical project-context revision from the audit-event cursor,
advances it once per logical structured mutation, freezes it explicitly on
durable workflow runs, and closes stale-snapshot and concurrent shared-object
write races. Its final focused checks passed 92 tests; PostgreSQL concurrency
checks passed 5 tests and migration round-trip/backfill checks passed 2 tests.
The final post-review backend suite passed 1,826 tests with zero failures, and
the frontend passed 53 files / 327 tests plus its production build.

This checkpoint does not assert completion of follow-up Stages F2-F10 or of the
corresponding partially implemented stages below.

---

# 1. Purpose

SiteWise generates and manages several major project artefacts:

- Project Management Plan (PMP)
- Cost Plan
- Request for Proposal (RFP)
- Request for Tender / RFQ (RFT)
- supporting schedules, registers, scope tables and project knowledge

The current system already contains valuable foundations:

- project taxonomy;
- building class;
- subclass;
- work type;
- scope;
- scale and complexity fields;
- profiler;
- project document retrieval;
- seed/platform knowledge;
- Markdown artefacts;
- Cost Plan structured data;
- inline paragraph editing;
- workbook editing;
- optimistic edit patterns;
- artefact versioning.

The next architectural step should make those foundations work together more coherently.

The target is not simply:

> generate better documents.

The target is:

> create living project artefacts that understand the evolving project, preserve human decisions, update incrementally and respond quickly.

---

# 2. Product North Star

The architecture should move from:

```text
Profiler
   ↓
Prompt
   ↓
LLM
   ↓
Whole Document
```

toward:

```text
Profiler ───────────────┐
Project Documents ──────┤
User Decisions ─────────┤
User Edits ─────────────┤
Seed Knowledge ─────────┘
          │
          ▼
Structured Project Context
          │
          ▼
Artefact-Specific Context
          │
          ▼
Addressable Objects
          │
          ▼
Small Validated Operations
          │
          ▼
Living Artefacts
```

The PMP, Cost Plan, RFP and RFT should eventually become different views of the same evolving project knowledge.

---

# 3. Core Architectural Principles

## 3.1 Perform the smallest amount of work required

Every user action should first be classified:

```text
Can application code do this?

Yes
→ perform deterministic operation

No
→ determine whether semantic AI reasoning is required

Does AI need retrieval?

No
→ use structured project context only

Yes
→ retrieve only relevant evidence
```

Avoid making AI the default implementation mechanism.

---

# 3.2 Human decisions have higher authority than generated content

Default authority order:

```text
Explicit user lock
        ↓
User-created content
        ↓
User-modified content
        ↓
Confirmed project evidence
        ↓
AI-generated content
        ↓
Seed assumptions
```

SiteWise should never silently destroy a user's previous work merely because an artefact is regenerated.

---

# 3.3 Project information has state

Every applicable profiler field should resolve to:

```text
KNOWN

UNKNOWN

EXPLICITLY_EXCLUDED

NOT_APPLICABLE
```

Do not simply remove unanswered fields.

An unanswered relevant question is useful project information.

---

# 3.4 Persistent identity is more valuable than text position

Source ranges tell SiteWise:

> where is this row right now?

Persistent IDs tell SiteWise:

> what project object is this?

Both are useful.

Ranges support rendering and editing.

IDs support long-term updates, relationships, provenance and preservation.

---

# 3.5 Regeneration should become incremental

Prefer:

```text
Project changed
↓
Determine what changed
↓
Determine what depends on it
↓
Update only affected objects
```

instead of:

```text
Project changed
↓
Regenerate everything
```

---

# 3.6 Performance and intelligence are the same problem

Smaller tasks generally produce:

- faster responses;
- fewer tokens;
- fewer retrieval calls;
- less accidental rewriting;
- more focused reasoning;
- easier debugging;
- better perceived quality.

Performance should therefore be designed into the architecture from the beginning.

---

# 4. Artefacts in Scope

The implementation must consider:

## PMP

Includes:

- narrative sections;
- project overview;
- project governance;
- risk;
- programme;
- design management;
- procurement;
- approvals;
- consultant schedules;
- FFE schedules;
- tables;
- lists.

## RFP

Includes:

- consultant scope;
- project context;
- deliverables;
- design responsibilities;
- interfaces;
- submission requirements;
- programme;
- procurement terms.

## RFT

Includes:

- package scope;
- inclusions;
- exclusions;
- design responsibilities;
- materials;
- interfaces;
- programme;
- logistics;
- quality requirements;
- testing and commissioning;
- tender returnables.

## Cost Plan

Includes:

- categories;
- cost items;
- allowances;
- budgets;
- forecasts;
- invoices;
- variations;
- commitments;
- totals;
- workbook/export representation.

---

# 5. Performance Targets

Establish targets in Stage 0.

Suggested initial UX targets:

```text
Hover / selection feedback           < 100 ms

Local UI edit                        < 150 ms

Optimistic structured edit           perceived immediate

Normal field save                    < 300–500 ms where practical

Panel / artefact opening             < 500 ms for primary UI

Structured backend mutation          ideally < 1 second

First AI acknowledgement             < 1 second

First useful AI output               as early as possible

Whole artefact completion            progressive, not blocking
```

Measure:

```text
TTFI
Time to First Interaction

TTFC
Time to First Content

TTFU
Time to First Useful AI Output

TTComplete
Total Completion Time
```

TTFU should become a primary SiteWise performance metric.

---

# STAGE 0 — Architecture Map, Baseline and Performance Instrumentation

## Objective

Understand the current system before modifying it.

No major behaviour changes.

## Tasks

### 0.1 Map all artefact generation paths

Trace:

```text
Create PMP
Update PMP

Create RFP
Update RFP

Create RFT
Update RFT

Create Cost Plan
Update Cost Plan
```

For each identify:

- API endpoint;
- workflow entry point;
- project profile loader;
- taxonomy resolver;
- scope resolver;
- seed selector;
- retrieval;
- model call;
- parser;
- persistence;
- renderer;
- frontend refresh path.

---

### 0.2 Identify duplicate logic

Search for repeated implementations of:

```text
building class
subclass
work type
scope
scale
complexity
profile formatting
seed routing
retrieval queries
artefact context building
version handling
```

Document duplicates.

---

### 0.3 Create regression fixtures

Create representative projects:

```text
Residential new build

Residential renovation

Commercial office fitout

Commercial refurbishment

Multi-residential

Industrial warehouse

Remediation

Complex staged occupied project
```

---

### 0.4 Add performance instrumentation

Measure:

```text
database time
retrieval time
seed-selection time
context-building time
LLM time
output-token time
frontend render time
payload size
retrieval count
LLM calls
database calls
```

---

### 0.5 Add interaction benchmarks

Especially measure:

```text
time to edit one paragraph

time to add one table row

time to delete one row

time to change one Cost Plan amount

time to add one cost item

time to update one profiler field
```

These measurements matter more to perceived speed than full generation time.

---

## Acceptance Criteria

- Current workflows documented.
- Performance baseline recorded.
- Existing tests pass.
- No behavioural regression.

---

# STAGE 1 — Canonical ProjectGenerationContext

## Objective

Create one authoritative structured interpretation of the project.

All artefact workflows should eventually consume this object.

---

## Proposed Concept

```python
class FieldState:
    KNOWN
    UNKNOWN
    EXPLICITLY_EXCLUDED
    NOT_APPLICABLE
```

```python
class ContextField:
    key
    label
    value
    state
    source
```

```python
class ProjectGenerationContext:
    project_id

    identity
    taxonomy

    scale
    complexity
    scope

    commercial
    programme
    approvals
    stakeholders

    derived_risks

    context_version
```

---

## 1.1 Resolve applicable profiler schema

Determine relevant profiler fields from:

```text
Class
+
Subclass
+
Work Type
```

Do not simply send every possible profiler field.

---

## 1.2 Preserve unanswered relevant fields

Example:

```text
Fire engineering required

state = UNKNOWN
value = null
```

---

## 1.3 Preserve explicit exclusions

Example:

```text
Facade works
state = EXPLICITLY_EXCLUDED
```

This is meaningfully different from unknown.

---

## 1.4 Add context versioning

Create:

```text
project_context_version
```

Increment when structured project information changes.

Examples:

- profiler edit;
- scope change;
- consultant change;
- confirmed extracted project fact;
- programme change;
- procurement change.

---

## 1.5 Cache project context

Cache by:

```text
project_id
+
project_context_version
```

At minimum reuse within a single request.

Use persistent caching only if measurement supports it.

---

## Acceptance Criteria

PMP, RFP, RFT and Cost Plan use the same canonical interpretation of taxonomy and profiler data.

---

# STAGE 2 — Artefact-Specific Context Lenses

## Objective

Provide each artefact only with information relevant to its function.

Use:

```python
build_pmp_context(project_context)

build_cost_plan_context(project_context)

build_rfp_context(project_context, discipline)

build_rft_context(project_context, package)
```

---

# 2A. PMP Context

Prioritise:

```text
taxonomy
scope
scale
complexity
client
stakeholders
programme
procurement
approvals
site constraints
risks
design constraints
commercial constraints
unknown critical information
```

---

# 2B. Cost Plan Context

Prioritise:

```text
taxonomy
scope
GFA
storeys
unit counts
quality level
existing/new split
services
site conditions
access
staging
occupied works
location
programme
procurement
known exclusions
cost evidence
```

---

# 2C. RFP Context

Prioritise:

```text
consultant discipline
taxonomy
scale
scope
design stage
complexity
required interfaces
programme
approvals
deliverables
design responsibilities
client requirements
```

---

# 2D. RFT Context

Prioritise:

```text
trade/package
scope
quantities
materials
finishes
interfaces
programme
staging
logistics
site access
existing conditions
testing
commissioning
design responsibilities
quality requirements
```

---

## Acceptance Criteria

Artefact workflows no longer manually reconstruct project-profile context.

**Implementation status (2026-08-10): complete.** Typed PMP, Cost Plan, RFP and
RFT lenses now project the frozen `ProjectGenerationContext` into focused prompt
inputs. Durable workflows derive the lens from their frozen run brief; direct
PMP/Cost Plan and retained consultant entry points resolve the same canonical
context from their snapshot. Procurement drafts persist the lens in provenance.
Seed routing, retrieval selection and renderer-internal compatibility helpers
were intentionally deferred to Stages 3-5.

---

# STAGE 3 — Unified Seed Knowledge Routing

## Objective

Create one routing system for PMP, RFP, RFT and Cost Plan.

Suggested interface:

```python
select_seed_knowledge(
    artefact_type,
    project_context,
    section=None,
    discipline=None,
    package=None,
)
```

Consider:

```text
artefact type
class
subclass
work type
scope
complexity
risk flags
discipline
package
section
```

---

## Cache seed routing

Cache:

```text
taxonomy
+
artefact type
+
seed version
```

Also cache parsed seed metadata and indexes.

Avoid repeatedly loading and reparsing unchanged seed knowledge.

---

## Acceptance Criteria

One shared routing system exists.

Old routing code is migrated or removed.

**Implementation status (2026-08-10): complete.** `select_seed_knowledge()` now
routes PMP, Cost Plan, consultant RFP and trade RFT/RFQ knowledge from the same
canonical project context. The cached key includes artefact/workflow, taxonomy,
scope, complexity, risk flags, target, section and a fingerprinted seed-routing
version. Parsed catalogue metadata, path indexes and PMP section maps are reused.
PMP's dedicated router was removed; source loaders and procurement candidate and
mandatory-guidance selection now consume the shared route plan.

---

# STAGE 4 — Retrieval Architecture & Parallelisation

## Objective

Reduce retrieval latency and duplication.

---

## 4.1 Separate structured facts from retrieval

Do not use RAG to rediscover information already known through:

```text
profiler
taxonomy
project facts
confirmed user edits
```

---

## 4.2 Introduce retrieval escalation

Use:

```text
LEVEL 0
Structured project facts only

LEVEL 1
Current artefact + profiler context

LEVEL 2
Targeted project retrieval

LEVEL 3
Broader corpus retrieval
```

Start at the lowest level likely to succeed.

---

## 4.3 Parallelise independent retrieval

Use bounded concurrency for independent searches.

Example:

```python
await asyncio.gather(
    retrieve_scope_evidence(),
    retrieve_programme_evidence(),
    retrieve_risk_evidence(),
)
```

Do not parallelise dependent operations.

---

## 4.4 Create generation evidence pools

Example:

```text
scope evidence
programme evidence
design evidence
approval evidence
cost evidence
procurement evidence
```

Reuse relevant evidence between sections.

Do not repeatedly query the same project corpus for essentially the same content.

---

## 4.5 Add retrieval budgets

Limit:

```text
search count
chunk count
token count
document count
```

Prefer high relevance over volume.

---

## Acceptance Criteria

Fewer redundant searches.

Parallel retrieval reduces wall-clock time.

Prompt context remains focused.

**Implementation status (2026-08-10): complete.** Generation retrieval now uses
typed escalation levels, hard search/chunk/document/character budgets and a
reusable evidence pool keyed by request and evidence category. Independent
procurement project and platform queries run with bounded concurrency on isolated
database sessions; their results are shared across downstream RFP/RFT rendering.
PMP and Cost Plan loaders now prefer structurally discoverable project evidence
and escalate to semantic retrieval only when that lower-cost evidence is
insufficient.

---

# STAGE 5 — Separate Deterministic Artefact Scaffold from AI Narrative

## Objective

Render useful artefact structure immediately.

This applies particularly to PMP, RFP and RFT.

---

## PMP Scaffold

Render immediately:

```text
PMP heading
project metadata
section headings
table structures
register headings
risk table
FFE table
known deterministic information
```

Narrative sections initially display:

```text
Preparing narrative…
```

---

## RFP Scaffold

Render immediately:

```text
project identity
discipline
scope headings
deliverables table
submission requirements
programme structure
known interfaces
```

Then generate narrative content progressively.

---

## RFT Scaffold

Render immediately:

```text
package identity
scope headings
inclusions
exclusions
returnables
programme
known interfaces
testing headings
```

Then enrich with AI.

---

## Cost Plan

The live Cost Plan grid is itself the scaffold.

Known deterministic categories/items should display immediately.

Missing estimates may show:

```text
TBC
```

or:

```text
Not yet estimated
```

AI enrichment should not block display.

---

## Acceptance Criteria

Time-to-first-content is dramatically lower than total generation time.

---

# STAGE 6 — Shared Artefact Generation Briefs

## Objective

Make concurrent section generation consistent.

---

## PMP Generation Brief

Create once per generation:

```text
project identity
taxonomy
scope
procurement model
programme
consultants
key risks
known terminology
major assumptions
project constraints
```

Every PMP section receives the same brief.

---

## RFP Generation Brief

Include:

```text
discipline
scope intent
project context
project stage
programme
interfaces
deliverables philosophy
procurement constraints
```

---

## RFT Generation Brief

Include:

```text
package
scope intent
interfaces
programme
logistics
quality requirements
design obligations
testing requirements
```

---

## Cost Plan Generation Brief

If AI is used for costing interpretation, provide:

```text
costing basis
taxonomy
scope
scale
quality assumptions
known exclusions
project location
programme/staging
```

Avoid sending the entire project corpus.

---

# STAGE 7 — Concurrent Section Generation

## Objective

Reduce full artefact generation time.

---

## 7.1 PMP

Split narrative into independent sections.

Run in bounded concurrency groups.

Start with:

```text
3–5 concurrent jobs
```

Measure before increasing.

---

## 7.2 RFP

Parallelise sections where independent:

```text
project overview
scope narrative
deliverables
interfaces
submission requirements
programme requirements
```

Do not parallelise where one section depends heavily on another.

---

## 7.3 RFT

Parallelise appropriate sections:

```text
scope narrative
interfaces
logistics
quality
testing
tender returnables
```

---

## 7.4 Cost Plan

Do not generate every row independently using AI.

Prefer deterministic structure.

Parallel AI interpretation may be useful only for clearly independent analytical tasks such as:

```text
scope coverage review
cost risk review
missing allowances review
```

---

## 7.5 Consistency validation

After concurrent narrative generation, perform a lightweight consistency check.

Prefer deterministic checks first:

```text
project name
consultant names
procurement terminology
scope duplication
duplicate risks
inconsistent dates
```

Use AI only for semantic conflicts that cannot be checked deterministically.

---

## Acceptance Criteria

Artefact wall-clock generation time improves without increasing inconsistency.

---

# STAGE 8 — Real Progress Events and Progressive Rendering

## Objective

Replace estimated/fake progress with actual progress.

---

## Backend Events

Emit events such as:

```text
context_ready

retrieval_complete

scaffold_ready

section_started

section_completed

validation_started

artefact_ready
```

---

## Frontend

Display:

```text
Project Overview        Complete

Scope                   Complete

Design Management       Generating

Risk Management         Queued
```

Use:

```text
7 of 11 sections complete
```

not invented percentages.

---

## Apply to

- PMP
- RFP
- RFT
- Cost Plan generation/import/rebuild where meaningful.

---

## Acceptance Criteria

Progress reflects real workflow state.

Users can review completed sections while other sections continue.

---

# STAGE 9 — Addressable Markdown Blocks

## Objective

Expand paragraph editing into reusable block editing.

Supported first:

```text
paragraph
list_item
table_row
```

---

## Frontend Target Type

Conceptually:

```typescript
type ArtifactBlockTarget = {
    id?: string;
    type: "paragraph" | "list_item" | "table_row";
    range: MarkdownRange;
};
```

---

## Refactor carefully

Replace paragraph-specific editing concepts with block concepts only where needed.

Avoid unrelated renderer changes.

---

## Acceptance Criteria

Rows and list items can become edit targets without breaking paragraph editing.

---

# STAGE 10 — General Optimistic Mutation Framework

## Objective

Reuse the successful Cost Plan / WorkbookGrid optimistic edit pattern.

Do not create a separate edit architecture for Markdown artefacts.

---

## Create shared behaviour

Conceptually:

```text
apply optimistic change
↓
enqueue mutation
↓
send version/revision
↓
server validates
↓
success
```

On conflict:

```text
409
↓
reload latest revision
↓
rebase where safe
↓
retry or show conflict
```

---

## Apply to

```text
PMP rows
RFP rows
RFT rows
list items
Cost Plan items
profiler values
structured project fields
```

---

## Acceptance Criteria

Simple edits feel immediate regardless of normal network latency.

---

# STAGE 11 — Manual Structural Editing

## Objective

Allow users to manipulate artefacts directly.

---

# PMP / RFP / RFT Tables

Support:

```text
Edit row

Add row above

Add row below

Duplicate row

Delete row
```

---

# Lists

Support:

```text
Edit

Add above

Add below

Duplicate

Delete
```

---

## FFE Example

```text
FFE-03 | Bathroom | Vanity | Timber veneer     ✦  ⋯
```

Menu:

```text
Edit
Add row
Duplicate
Delete
```

---

## Implementation

Centralise operations:

```text
replaceBlock()

insertBeforeBlock()

insertAfterBlock()

deleteBlock()
```

Do not duplicate string manipulation inside components.

---

## Acceptance Criteria

FFE and similar schedules are manually editable.

The same framework works across PMP, RFP and RFT.

---

# STAGE 12 — Persistent Block Identity & Provenance

## Objective

Give artefact content long-term identity.

---

## Minimum metadata

```text
id
created_by
last_modified_by
updated_at
```

Later:

```text
source_refs
user_protected
status
```

---

## Creation sources

```text
user
ai
import
system
```

---

## Important

Block IDs should remain stable even when surrounding Markdown changes.

---

## Acceptance Criteria

A manually edited row remains identifiable during later updates.

---

# STAGE 13 — Dirty Flags and Dependency Tracking

## Objective

Know exactly what changed and what depends on it.

---

## Dirty Categories

Examples:

```text
scope_dirty

programme_dirty

cost_dirty

consultants_dirty

ffe_dirty

approvals_dirty

design_dirty

procurement_dirty
```

---

## Dependency Map

Example:

```text
hydraulic_consultant
    ↓
PMP consultant register
Hydraulic RFP
possibly Cost Plan consultant fees
```

---

## Another example

```text
bathroom finish change
    ↓
PMP FFE
Cost Plan finishes
Bathroom trade RFT
```

Not:

```text
PMP governance
structural RFT
programme
```

---

## Acceptance Criteria

The system can determine affected artefact objects without regenerating unrelated artefacts.

---

# STAGE 14 — Safe Incremental Artefact Updates

## Objective

Preserve previous user work when new project context is added.

Use three-way semantic merge principles.

---

## Inputs

```text
BASELINE
previous AI-generated state

CURRENT
current user-edited state

NEW PROJECT STATE
latest project context/evidence
```

---

## Protection Rules

### AI-created untouched

May auto-update.

### AI-created user-modified

Preserve unless new evidence creates a conflict requiring review.

### User-created

Preserve by default.

### User-locked

Never auto-update.

---

## Deletion

Use:

```text
PROPOSE_DELETE
```

for user-created/user-modified content.

Do not silently delete it.

---

## Acceptance Criteria

Manual changes survive later PMP/RFP/RFT updates.

---

# STAGE 15 — AI Structural Operations

## Objective

Convert natural language into small structured operations.

---

## Example PMP

User:

> Add filtered water taps to the kitchen and staff breakout area.

AI returns:

```json
{
  "operations": [
    {
      "type": "add_row",
      "target": "ffe_schedule",
      "values": {
        "area": "Kitchen",
        "item": "Filtered water tap"
      }
    }
  ]
}
```

Application code performs the insertion.

---

## RFP Example

User:

> Add acoustic coordination with the mechanical consultant to the architect's scope.

Operation:

```text
ADD_SCOPE_ITEM
Architect RFP
Acoustic/mechanical coordination
```

---

## RFT Example

User:

> Add commissioning certificates to the mechanical tender returnables.

Operation:

```text
ADD_RETURNABLE
Mechanical RFT
Commissioning certificates
```

---

## Validation

Validate:

```text
operation
target
revision
schema
required fields
permissions
```

---

## Acceptance Criteria

AI modifies only relevant artefact objects.

---

# STAGE 16 — AI Task Routing

## Objective

Use the fastest adequate execution path.

Classify tasks:

```text
DETERMINISTIC

FAST_SEMANTIC

REASONING

NARRATIVE
```

---

## Examples

### Deterministic

```text
Change cost amount
Delete row
Move row
Change consultant
```

No model.

---

### Fast Semantic

```text
"Add a suitable kitchen mixer."
```

Small/fast model.

---

### Reasoning

```text
"Reconcile conflicting hydraulic requirements."
```

Strong reasoning model.

---

### Narrative

```text
"Write the Design Management section."
```

Narrative-capable model.

---

## Acceptance Criteria

Small tasks do not use the most expensive reasoning path by default.

---

# STAGE 17 — Cost Plan Canonical State & Fast Editing

## Objective

Ensure the Cost Plan UI is driven by structured state rather than workbook regeneration.

---

## Desired model

```text
Canonical Cost Plan
      │
      ├── live UI
      ├── calculations
      └── workbook export
```

Avoid:

```text
edit
↓
generate XLSX
↓
reload XLSX
↓
refresh UI
```

---

## Support

```text
add cost item

edit cost item

delete cost item

move cost item

duplicate cost item

add category

delete category
```

---

## Dependencies

Before deleting:

```text
check invoices
check commitments
check variations
check forecasts
check procurement references
```

Block unsafe deletion.

---

## Acceptance Criteria

Common Cost Plan edits update instantly and do not require workbook regeneration.

---

# STAGE 18 — Batch and Debounce Workbook Rebuilds

## Objective

Reduce repeated XLSX generation.

---

## Example

Instead of:

```text
invoice edit
→ rebuild workbook

invoice edit
→ rebuild workbook

cost edit
→ rebuild workbook
```

use:

```text
multiple edits
↓
coalesce changes
↓
one workbook regeneration
```

Workbook generation should happen:

- on explicit export;
- when preview genuinely requires it;
- after a sensible quiet period;
- or when a persisted workbook version must be updated.

---

## Acceptance Criteria

Rapid cost/invoice editing does not repeatedly rebuild the entire workbook.

---

# STAGE 19 — AI Cost Plan Operations

## Objective

Use AI to interpret requests but deterministic code to mutate the Cost Plan.

---

## Example

User:

> Add $50,000 for loose furniture and $25,000 for AV equipment.

AI returns:

```text
ADD_COST_ITEM
Loose Furniture
$50,000

ADD_COST_ITEM
AV Equipment
$25,000
```

Application validates and performs the operations.

---

## Acceptance Criteria

AI never edits workbook text directly.

---

# STAGE 20 — Cross-Artefact Project Knowledge

## Objective

Allow one project fact to inform multiple artefacts.

Start small.

---

## High-value shared objects

```text
consultants
stakeholders
scope items
FFE
cost items
milestones
procurement packages
key project decisions
```

---

## Example

Change:

```text
Hydraulic Consultant:
ABC → Fluid Design
```

SiteWise identifies:

```text
PMP
Hydraulic RFP
Consultant Register
possibly Cost Plan
```

and asks whether dependent references should update.

---

## Important

Do not build a complex generic graph database initially.

Use explicit relationships first.

---

# STAGE 21 — Block-Level Input Hashing

## Objective

Skip regeneration when relevant inputs have not changed.

Store per block:

```text
context version
source version
seed version
input hash
generation version
```

Then:

```text
new input hash == old input hash
```

means:

```text
skip regeneration
```

This turns artefact updates into an incremental build system.

---

# STAGE 22 — Generation Audit / Why This?

## Objective

Make artefact generation explainable.

Persist a generation manifest.

Example:

```text
Taxonomy

Commercial
Office
Refurbishment


Known profile

GFA: 4,200m²
Occupied building: Yes


Unknown relevant fields

Fire engineering
Heritage status


Evidence used

Architectural Brief Rev C
Services Report
Client Requirements


Seed knowledge

Commercial refurbishment
Occupied projects
Mechanical services
```

---

## Apply to

- PMP
- RFP
- RFT
- Cost Plan.

---

## User-facing view

A simple:

```text
Sources & Context
```

drawer.

Detailed developer view can show more.

---

# STAGE 23 — Frontend Responsiveness Pass

## Objective

Optimise actual measured frontend bottlenecks.

Possible techniques only where profiling supports them:

```text
local edit state
debounced saves
stable object IDs
lazy module loading
code splitting
memoisation
virtualised long tables
small delta updates
```

Avoid blanket optimisation.

---

## Large Lists

Consider virtualisation for:

```text
large Cost Plans
large document registers
large consultant schedules
large tender tables
large FFE schedules
```

Do not virtualise small lists.

---

# STAGE 24 — Database and Payload Optimisation

## Objective

Remove unnecessary backend latency.

Profile for:

```text
N+1 queries
repeated project lookups
unindexed filters
large JSON payloads
sequential reads
duplicate writes
```

---

## Batch Operations

If AI adds five rows:

Prefer:

```text
POST operations [
  row1,
  row2,
  row3,
  row4,
  row5
]
```

One transaction.

One revision increment.

One response.

---

## Delta Responses

After changing one item, return:

```text
updated object
affected totals
new revision
```

Not the entire artefact unless necessary.

---

# STAGE 25 — Full Simplification Pass

## Objective

Once the new architecture is stable, deliberately remove old complexity.

---

## Delete obsolete implementations

Search for superseded:

```text
context builders
seed routers
retrieval helpers
paragraph-only edit functions
full-document regeneration helpers
workbook-preview mutation paths
duplicate optimistic mutation code
```

---

## Avoid permanent V2 implementations

Bad:

```text
old_context()
new_context_v2()
new_context_final()
```

Good:

```text
resolve_project_generation_context()
```

---

## Collapse common operations

Aim toward one operation model:

```text
ADD
UPDATE
DELETE
MOVE
DUPLICATE
```

Target types:

```text
paragraph
list_item
table_row
cost_item
project_fact
```

---

# 6. Common Operation Model

Long term:

```json
{
  "operation": "UPDATE",
  "target_type": "table_row",
  "target_id": "ffe_8f31a7",
  "changes": {
    "finish": "Honed Carrara Marble"
  }
}
```

Manual UI, AI operations and backend services should gradually converge on this vocabulary.

---

# 7. Versioning and Concurrency

All structured mutations should follow:

```text
read current revision
↓
validate operation
↓
confirm revision
↓
apply
↓
increment revision
↓
record provenance
```

Reject stale mutations rather than blindly applying them.

---

# 8. Audit Trail

Eventually record:

```text
who
when
operation
target
previous value
new value
source
reason
```

The full audit UI can come later.

Preserve the data model now.

---

# 9. Performance Guardrails

Add architectural tests.

Example:

## Row edit

Must produce:

```text
0 LLM calls
0 RAG calls
1 mutation
```

---

## Profiler field save

Must not automatically regenerate all artefacts.

---

## Cost Plan amount edit

Must not rebuild the workbook solely to update the live grid.

---

## Small AI row addition

Should not retrieve the full project corpus when structured context is sufficient.

---

# 10. Recommended Implementation Order

Execute in this sequence:

```text
0  Architecture map + performance baseline

1  Canonical ProjectGenerationContext

2  Artefact-specific context lenses

3  Unified seed routing

4  Retrieval optimisation + parallelisation

5  Immediate deterministic artefact scaffolds

6  Shared generation briefs

7  Concurrent PMP/RFP/RFT section generation

8  Real progress events + progressive rendering

9  Addressable Markdown blocks

10 Shared optimistic mutation framework

11 Manual row/list editing

12 Persistent block identity + provenance

13 Dirty flags + dependency tracking

14 Safe incremental semantic updates

15 AI structural operations

16 AI task/model routing

17 Canonical Cost Plan state + fast editing

18 Batched/debounced workbook generation

19 AI Cost Plan operations

20 Cross-artefact project knowledge

21 Block-level input hashing

22 Generation audit / explainability

23 Frontend profiling + responsiveness

24 Database/payload optimisation

25 Code simplification and removal of obsolete paths
```

---

# 11. Early Performance Milestone

An important milestone should occur after Stage 11.

At that point:

```text
PMP/RFP/RFT scaffold appears immediately

narrative generates progressively

retrieval runs concurrently where appropriate

real progress is visible

table rows can be edited immediately

row edits do not use AI

optimistic mutation is shared

project context is canonical

seed routing is cached
```

This should produce a visible improvement in product responsiveness before the full architecture is complete.

---

# 12. End-State User Scenarios

## Scenario A — PMP Generation

User clicks:

```text
Create PMP
```

Within moments they see:

```text
PMP

Project Overview
Scope
Governance
Risk
Design
Procurement
FFE
...
```

Known tables are already populated.

Narrative sections fill progressively.

---

## Scenario B — RFP Generation

User creates an Architect RFP.

The shell appears immediately:

```text
Project
Scope
Deliverables
Interfaces
Programme
Submission Requirements
```

Narrative sections generate concurrently.

---

## Scenario C — RFT Generation

User creates a Mechanical RFT.

Known project scope, interfaces and tender structures appear immediately.

Detailed package wording fills progressively.

---

## Scenario D — FFE Edit

User adds:

```text
Filtered water tap
```

The row appears instantly.

SiteWise saves it.

No AI.

No retrieval.

No PMP regeneration.

---

## Scenario E — Later PMP Update

User uploads revised drawings.

SiteWise determines that:

```text
FFE
Design Management
Risk
```

are affected.

Only those areas update.

Previously user-added FFE rows are preserved.

---

## Scenario F — RFP Update

The hydraulic consultant scope changes.

SiteWise updates the relevant RFP scope items and interfaces.

Unrelated consultant RFPs remain untouched.

---

## Scenario G — RFT Update

A project programme changes.

SiteWise identifies which tender packages rely on the affected dates.

Only relevant programme requirements update.

---

## Scenario H — Cost Edit

User changes:

```text
Joinery
$72,000 → $80,000
```

UI updates immediately.

Category and project totals recalculate.

No workbook rebuild is required for the live view.

---

## Scenario I — Cost Plan AI

User says:

> Add $60,000 for loose furniture.

SiteWise creates one structured cost item.

It does not regenerate the Cost Plan.

---

## Scenario J — Conflicting Information

User previously changed:

```text
Hydraulic consultant = Fluid Design
```

A new old document says:

```text
ABC Engineering
```

SiteWise raises a conflict.

It does not silently revert the user edit.

---

# 13. Final Architectural North Star

SiteWise should eventually behave more like an intelligent incremental project system than a collection of AI document generators.

The desired execution model is:

```text
USER ACTION
       │
       ▼
CLASSIFY INTENT
       │
       ▼
CAN APPLICATION CODE DO IT?
       │
 ┌─────┴─────┐
 YES         NO
 │            │
 ▼            ▼
DO IT      IDENTIFY TARGET
NOW            │
               ▼
        LOAD MINIMUM CONTEXT
               │
               ▼
      RETRIEVE ONLY IF NEEDED
               │
               ▼
       USE SMALLEST ADEQUATE
           AI CAPABILITY
               │
               ▼
       VALIDATE OPERATIONS
               │
               ▼
      UPDATE AFFECTED OBJECTS
               │
               ▼
        DISPLAY PROGRESSIVELY
```

The key consequence is that:

**small changes remain small.**

A user changing one row should not invoke a project-wide reasoning process.

A new document should not cause every artefact to be regenerated.

A Cost Plan edit should not require rebuilding an Excel workbook before the user can see the change.

An RFP scope adjustment should not regenerate unrelated procurement artefacts.

A PMP should become visible before its complete narrative has finished generating.

---

# 14. Definition of Success

The implementation is successful when SiteWise feels like:

> a fast, responsive project-management application with deep intelligence

rather than:

> an AI application that frequently asks the user to wait for documents to regenerate.

The architecture should simultaneously improve:

- speed;
- output quality;
- user control;
- preservation of human decisions;
- project-context consistency;
- maintainability;
- observability;
- model efficiency;
- adoption;
- trust.

The most important technical behaviours are:

```text
canonical context

incremental updates

addressable objects

persistent identity

optimistic mutation

parallel independent work

progressive rendering

real progress events

small AI tasks

structured operations

deterministic application logic

cached stable knowledge

targeted retrieval

dependency-aware regeneration
```

Together, these should become the architectural foundation for the next major evolution of SiteWise.
