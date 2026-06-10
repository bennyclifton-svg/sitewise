# Workflows & Tender Evaluation — Planning Notes

> Companion to [todoist.md](../todoist.md) Phases 11–12. Implement **after** Phases 6–9 (ingestion, retrieval, doctrine-grounded chat).

**Goal:** Clerk moves from **answering questions** about the corpus to **running repeatable PM processes** (skills) and **tender evaluation** — always under [clerk-brief.md](../clerk-brief.md) and `seed/` reference knowledge.

---

## Why this is a separate phase

Chat + retrieval (Phases 6–9) must be trustworthy first. Deliverable workflows and tender evaluation are **multi-step, high-stakes outputs** where:

- Doctrine governs *how* to think (§05-procurement, §evidence-discipline, §escalation-triggers)
- Seed governs *domain depth* (procurement-quoting-guide, tender-evaluation patterns, cost-management-principles)
- Project evidence governs *facts* (RFT criteria, submission prices, qualifications)
- Exemplar TRRs in the corpus show *what good looks like* for output structure

Building workflows on a weak retrieval layer produces polished wrong answers — worse than “insufficient evidence.”

---

## Corpus as exemplars

| Folder | Workflow value |
| ------ | -------------- |
| `procurement-blockb/` | **Primary validation** — 210 files, doctrine-aligned folder tree: `01 TEP` → `08 TRR`; two submission sets + evaluation + TRR (9 files) |
| `procurement-campy/` | Scale test — 655 files, submissions + recommendation at largest size |
| `procurment-demo/` | Pipeline smoke only — too thin for evaluation quality tests |
| `delivery-house/` / `delivery-petersham/` | Delivery workflows (claims, variations, PC) — Phase 11 stretch |
| `seed/` + `clerk-brief.md` | Always consulted for procurement and deliverable tasks |

`procurement-blockb/` structure (on disk):

```text
procurement-blockb/
├── 01 TEP
├── 02 EOI
├── 03 RFT
├── 04 ADDENDUM
├── 05 SUBMISSION 01
├── 06 EVALUATION
├── 07 SUBMISSION 02
└── 08 TRR
```

Ingestion must preserve `procurement_stage` in `document_metadata` so retrieval can scope “only submission 01” or “only TRR.”

---

## Phase 11 — Deliverable workflows (skills)

### User intents (examples)

- “Write me a project management plan”
- “Create a request for tender” / “Draft an RFP”
- “Prepare a cost plan”
- “Create a programme outline”

### Architecture sketch

```mermaid
flowchart LR
  user[User request] --> detect[Intent + workflow detect]
  detect --> gate[§seed-consultation gate\narchetype / role / state]
  gate --> skill[Load workflow skill spec]
  skill --> retrieve[Retrieval scoped to project]
  retrieve --> doctrine[Doctrine + seed passages]
  doctrine --> run[Structured generation]
  run --> validate[Grounding + evidence labels]
  validate --> stream[Stream to chat + persist]
```

### Skill sources

Existing SiteWise skills (e.g. procurement-process, tender-evaluation, master-programme, cost-planning) inform structure. Clerk re-authors them as:

```text
backend/app/workflows/skills/
├── pmp.yaml              # steps, required inputs, output schema, seed_consulted list
├── rft.yaml
├── cost-plan.yaml
├── programme.yaml
└── procurement-strategy.yaml
```

Each skill defines:

- **Trigger phrases** — when to invoke vs free-form chat
- **Required context** — project folder, declarations, minimum retrieved doc classes
- **Steps** — ordered sub-tasks (e.g. RFT: scope baseline → evaluation criteria → tender period → returnables)
- **Output schema** — Pydantic model for typed draft
- **Doctrine hooks** — which clerk-brief sections apply
- **Seed files** — mandatory consultation list per §seed-consultation-discipline

### §seed-consultation gate

Before any phase-gate deliverable, agent must confirm `archetype`, `user_role`, `state` (from project context — thread metadata or project README when active-project UX exists). If missing: **stop and ask**; do not guess.

### Chat integration

- Phase 11a: workflow invoked explicitly (“/workflow rft” or button) with project selector
- Phase 11b: agent detects intent from natural language and confirms before long run

### Done criteria

One workflow (recommend: **procurement strategy note** or **RFT outline**) runs on `procurement-blockb/` with:

- Retrieved RFT + TEP passages cited
- `procurement-quoting-guide.md` / doctrine cited where rules apply
- Assumptions labelled
- Output persisted to thread

---

## Phase 12 — Tender evaluation

### Problem shape

Mid-project, tender submissions arrive (often ZIPs, many PDFs per bidder). The PM must:

1. Ingest and index each submission
2. Compare against RFT evaluation criteria (price + non-price, evaluated separately per doctrine)
3. Iterate in chat (“What did Tenderer 02 assume about latent conditions?”)
4. Produce a **tender recommendation report** grounded in evidence

The corpus already contains **completed examples** — Block B and Campy TRRs plus the submissions they evaluated.

### Ingestion requirements (feeds Phase 6)

| Metadata field | Example | Used for |
| -------------- | ------- | -------- |
| `procurement_stage` | `submission_01`, `evaluation`, `trr` | Folder-based filter |
| `tenderer_id` | `submission_01` → map to bidder name from index file or folder | Per-bidder retrieval |
| `document_class` | `tender_submission`, `evaluation_matrix`, `trr` | Class routing |
| `package_name` | `head_contract` | Multi-package tenders |

### Retrieval patterns

- “Summarise evaluation criteria” → `06 EVALUATION` + `03 RFT` only
- “Compare price across tenderers” → all `tender_submission` docs, structured extraction later (Phase 12b)
- “How did the exemplar TRR structure the recommendation?” → `08 TRR` as **format exemplar** + doctrine; separate from live project facts

### Tender evaluation workflow skill

Port/adapt `tender-evaluation` skill:

1. Load evaluation criteria from retrieved RFT/evaluation docs
2. Per tenderer: retrieve submission summary chunks (qualifications, exclusions, programme)
3. Build comparison matrix (schema — not free prose)
4. Draft recommendation sections: shortlist rationale, price analysis, non-price analysis, risks, recommendation
5. Cite every row in matrix to submission passage
6. Compare draft structure to exemplar TRR in corpus (style/section checklist, not copying conclusions)

### Iterative chat

Tender evaluation is **many turns** — user drills into one tenderer, one criterion, one qualification. Requirements:

- Thread retains `active_project` + `procurement_stage` scope
- Agent tools: `search_documents(project, stage, tenderer?)`, `read_chunk`, `compare_tenderers(criterion)` (Phase 12b)
- Doctrine reminder on price/non-price separation and auditable RFI/addenda process

### Validation queries (Block B)

After ingest + Phase 8/12:

- “What are the Block B evaluation criteria?”
- “What price qualifications did Submission 01 include?”
- “How does the Block B TRR justify the recommended tenderer?”
- “Draft a comparison of Submission 01 vs Submission 02 on programme risk” (workflow)

Golden tests: compare agent-cited TRR conclusions to known Block B TRR text (integration).

### Scale path

| Step | Folder | Files | Purpose |
| ---- | ------ | ----- | ------- |
| 1 | `procurement-blockb/` | 210 | Validate evaluation + TRR retrieval |
| 2 | `procurement-industrial-new/` | 25 | Small full package with TRR |
| 3 | `procurement-campy/` | 655 | Scale, DWG register, large submission sets |

---

## What to consider now (Phase 6) so Phases 11–12 are not blocked

| Decision | Phase 6 action |
| -------- | -------------- |
| `procurement_stage` metadata | Parse from folder names like `05 SUBMISSION 01` |
| `document_class` includes tender types | `tender_submission`, `trr`, `evaluation`, `rft`, `addendum` |
| `document_metadata` JSONB | Room for `tenderer_id`, `package_name`, drawing register fields |
| Ingest order includes blockb | Before campy; primary tender test corpus |
| ZIP submissions | Expand and re-classify in Phase 6b (blockb has 4 zips) |
| MSG correspondence | Phase 6b — tender Q&A often in `.msg` (42 in blockb) |

---

## Non-goals (Phases 11–12 v1)

- Automated price spreadsheet parsing from all bid formats (manual/assisted summary first)
- Replacing human sign-off on TRR
- Live tender portal integration
- Multi-tenant project isolation (single corpus / project selector sufficient for v1)
