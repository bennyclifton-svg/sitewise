# Seed-backed human-in-the-loop decisions

Date: 2026-07-12

Status: validated design (ready for implementation planning)

Audience: product owner + implementation agents

Related:

- Existing PMP decision machinery: `backend/app/sitewise/pmp_decisions.py`,
  `frontend/src/components/project/DecisionControl.tsx`
- Platform seed knowledge: `data/seed/`
- TCM PRD: `docs/plans/2026-06-11-tender-comparison-module-prd.md`
- TCM speed strategy: `docs/plans/2026-07-11-tcm-speed-and-mvp-refactor-strategy.md`

---

## 1. Problem

Clerk already has an excellent PMP pattern: the agent embeds multiple-choice
decisions in the draft, pre-selects the best option, and lets the user override.
Overrides lock (`source: "user"`) and survive Create/Update PMP reruns, with
conflict surfacing when the agent would have picked differently.

That pattern is underused. Sparse briefs often leave the PMP thin. Cost plan has
no equivalent. Tender Comparison has related ideas (adjudication candidates, QA
accept/correct) but not the same inline pre-select + override UX, and does not
reuse the project decision store for shared context.

We want more human-in-the-loop definition of the project — especially when the
profiler says “standard house” but the brief/scope evidence is thin — without
turning drafts into walls of unanswered forms.

---

## 2. Product decisions (locked)

| Topic | Decision |
| --- | --- |
| Selection semantics | Always pre-select; user overrides only when wrong (same as today) |
| Sparse-brief aggressiveness | Moderate — curated checklist per building type |
| UI surface | Inline only in the draft (no assumptions panel) |
| Cost plan | Same decision-control pattern in this effort |
| PMP ↔ cost plan | Hard sync on shared `decision_id` keys |
| On shared flip that affects numbers | Restamp selection only; regenerate figures on explicit Update Cost Plan |
| Option vocabulary | Curated catalogs from seed knowledge + agent extras |
| Catalog home | Structured decision blocks **inside existing** `data/seed/` files |
| Density | ~10–15 curated decisions for a typical sparse residential brief |
| First wave domains | Brief & finishes-led, plus today’s core procurement/contract decisions |
| Agent extras | May invent a few new questions and/or option values when justified; stay near the 10–15 band |
| Seed research | During implementation, research and enrich seed decision blocks for a comprehensive, high-quality question set — not a thin stub |

### Tender Comparison

| Topic | Decision |
| --- | --- |
| Rollout | Both surfaces, **intake first**, matrix later |
| Shared project decisions | Reuse shared keys only — tender pre-fills from `project_decisions`; overrides update the same locked row |
| Tender-only intake fields | Keep today’s static intake controls |
| Matrix cell meaning | Inline flip overrides adjudicated mapping as a locked correction |
| QA relationship | Inline replaces QA for those item types (no parallel queue) |
| When to show cell options | Whenever adjudication had 2+ candidates; winner pre-selected |

---

## 3. Design

### 3.1 Seed-embedded decision catalogs

Relevant seeds (first wave: finishes / brief-scope domains, plus existing
procurement and contract cores) gain structured decision blocks alongside prose.

Illustrative shape (exact fence/format chosen at implementation):

```yaml
decision:
  id: flooring-finish
  section: Brief and scope
  label: Primary flooring finish
  applies_to:
    archetypes: [new-dwelling, renovation]
    classes: [residential]
  options:
    - { value: timber, label: Timber flooring }
    - { value: engineered, label: Engineered timber }
    - { value: tile, label: Tile }
    - { value: carpet, label: Carpet }
  default_hint: engineered
```

**Runtime**

1. Create/Update PMP loads applicable seeds via existing seed routing.
2. Workflow builds an **allowed decision set** (~10–15 for sparse residential):
   core PMP decisions + filtered seed decisions for underspecified brief areas.
3. Agent emits a `pmp-decision` (or shared) fence for each required id, with
   `selected` always set (`source: "agent"` unless already user-locked).
4. Agent extras: small cap of new questions and/or option values when evidence
   justifies; still pre-selected; total near the band.
5. User override → `source: "user"` in `project_decisions`, restamp on regenerate
   — existing semantics unchanged.
6. `evidence_conflict` / `agent_suggestion` behavior on restamp remains.

**Implementation note:** Do not ship a placeholder catalog. Research against seed
prose (and construction practice for NSW residential Class 1a where relevant)
to identify the best comprehensive question/option sets, then store and retrieve
them from the seed files.

### 3.2 Cost plan decisions + hard sync

- Cost plan drafts use the **same** fenced decision control contract and UI
  (`DecisionControl` / markdown interceptor).
- Shared keys (e.g. `contract-form`, finish/scope ids that affect allowances)
  live in one `project_decisions` row. Changing either draft updates that row
  and **restamps** the selection in both latest drafts.
- Cost **numbers** do not auto-recalculate. Locked selections are injected into
  the next Update Cost Plan prompt; figures refresh only on that explicit run.
- Cost-only decisions (e.g. contingency band, PC/PS treatment, inclusions
  baseline) use the same UX but do not restamp PMP.
- Conflict handling matches PMP: locked user choice wins; agent disagreement is
  surfaced, not auto-unlocked.

### 3.3 Tender Comparison (phased)

**Phase A — Intake**

- When opening/running tender on a project, pre-fill intake from shared
  `project_decisions` where keys overlap.
- Render those fields with the decision-control UX.
- Overrides update the shared row and restamp PMP/cost draft selections.
- Tender-only fields remain today’s static intake forms.

**Phase B — Matrix**

- Where adjudication produced multiple candidate mappings, render an inline
  choice control on the cell: candidates as options, winner selected.
- User flip = locked mapping correction (same class of truth as today’s QA
  `correct`).
- Those multi-candidate item types leave the QA queue once inline exists.
- QA remains for item types that do not yet have inline controls.
- Arithmetic stays Python; choices only change classification/mapping inputs.
- Audit who/when/previous value on override (reuse QA correction audit shape
  where practical).

---

## 4. Non-goals

- No separate project-wide “assumptions panel” in this design.
- No auto-regeneration of cost figures on decision flip.
- No free-text answers as the primary control (options remain enumerated;
  agent extras are still discrete options).
- No early rewrite of legacy chat/Polar; this extends SiteWise draft workflows
  and TCM surfaces only.
- TCM taxonomy ledger is not the Cost Plan workbook (see TCM speed strategy).

---

## 5. Suggested delivery order

1. **Seed research + catalog enrichment** for brief/finishes-led decisions in
   existing seed files; parser for structured decision blocks.
2. **PMP allowed-set assembly** (~10–15) + prompt/validation updates; keep
   lock/restamp/conflict behavior.
3. **Cost plan decision fences** + shared-key hard sync + restamp-only on flip.
4. **TCM Phase A** — intake pre-fill from shared decisions.
5. **TCM Phase B** — matrix multi-candidate inline overrides; retire those items
   from the QA queue.

---

## 6. Success criteria

- Sparse residential PMP ships with a curated ~10–15 decision set, all
  pre-selected, overrideable inline.
- User can flip a shared decision in PMP or cost plan and see the selection
  update in both drafts without a regenerate; cost numbers wait for Update Cost
  Plan.
- Seed files are the durable home of curated question/option catalogs.
- Tender intake reflects shared project decisions; later, contested matrix cells
  are fixable inline without a duplicate QA path for those items.
