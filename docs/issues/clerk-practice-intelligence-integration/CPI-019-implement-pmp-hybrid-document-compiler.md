---
title: Implement PMP Hybrid Document Compiler
status: draft
type: AFK
triage_label: needs-triage
labels: [needs-triage, clerk, sitewise, workflows, create-pmp, performance]
source: docs/plans/2026-06-08-sitewise-document-compiler-hybrid-prd.md
user_stories: []
depends_on:
  - CPI-009-run-create-pmp-through-clerk-workflow-runtime.md
  - CPI-017-port-practice-document-metadata-extraction.md
---

# Implement PMP Hybrid Document Compiler

## Parent

[SiteWise Document Compiler — Hybrid Workflow PRD](../../plans/2026-06-08-sitewise-document-compiler-hybrid-prd.md)

## Problem

Create PMP is too slow and too variable when a single LLM call generates the entire PMP. Prompt tuning alone does not converge. Market adoption requires first useful draft in ~10–15 seconds with evidence-faithful facts.

## Solution

Replace the monolithic `run_create_pmp_model` path with:

1. **Extract** → `MobilisationEvidencePack`
2. **Render** → template scaffold (~70–80% of markdown)
3. **Narrate** → small LLM for judgements, recommendations, register rows
4. **Assemble + validate + save** (existing QA layer)

Keep legacy full-doc path behind `PMP_HYBRID_COMPILER` env flag until hybrid is default.

## Implementation phases (grab one issue slice at a time)

### Phase 1 — Evidence pack extractor

- [ ] Add `backend/app/sitewise/mobilisation_evidence.py` with `MobilisationEvidencePack` dataclass/Pydantic model
- [ ] Implement `extract_mobilisation_evidence_pack(source_texts, evidence_refs) -> MobilisationEvidencePack`
- [ ] Parse Harrison Clarke engagement letter + fee proposal fields per PRD field spec
- [ ] Unit tests: `backend/tests/sitewise/test_mobilisation_evidence.py` against `data/synthetic-mobilisation-evidence/`
- [ ] Do **not** wire into workflow yet

**Handoff prompt:** *Implement CPI-019 Phase 1 only.*

### Phase 2 — PMP scaffold renderer

- [ ] Add `backend/app/sitewise/pmp_renderer.py` with `render_pmp_scaffold(project, pack, draft_mode) -> str`
- [ ] Render all `required_section_headings("architect-pm")` except narrative-heavy audit/risk slices
- [ ] Reuse checklist strings from `pmp_greenfield_brief.py` (import, do not duplicate)
- [ ] Snapshot or assertion tests for Harrison Clarke pack

### Phase 3 — Narrative LLM slice

- [ ] Add `backend/app/workflows/pmp_narrative.py` + `pmp_narrative_instructions.md`
- [ ] Structured output: judgements, recommendations (≥3 with ISO dates), register rows table, workflow warnings
- [ ] Small prompt only; no full doctrine paste

### Phase 4 — Assembler + workflow wire-up

- [ ] Add `backend/app/sitewise/pmp_assembler.py` → `assemble_pmp_markdown(scaffold, narrative, provenance)`
- [ ] Update `run_create_pmp_workflow` to call extract → render → narrate → assemble when flag enabled
- [ ] Retry narrative only on validation failure

### Phase 5 — Flag, integration test, default hybrid

- [ ] `PMP_HYBRID_COMPILER` in `backend/app/config.py`
- [ ] Integration test: full hybrid run on Harrison Clarke fixture (mock narrative LLM if needed)
- [ ] Document flag in `backend/.env.example`
- [ ] Flip default to hybrid when stable

### Phase 6 — Cost plan compiler (separate grab)

- [ ] Replicate pattern for `create_cost_plan.py` using `cost_plan_brief.py`

## Acceptance criteria (Test Project 112 / Harrison Clarke)

See PRD section **Quality bar — acceptance criteria**. All automated checks must pass; content checklist must match v09+ improvements including September 2026 DA target, register rows, fee staging, Linden conflict.

## Performance targets

- Scaffold + extract: < 500 ms
- End-to-end hybrid: < 15 s p95 (single narrative LLM call)

## Out of scope

- Cursor SDK as core generator
- Replacing Update PMP in Phase 1–4 (follow-on after Create PMP hybrid stable)

## References

- PRD: `docs/plans/2026-06-08-sitewise-document-compiler-hybrid-prd.md`
- Current workflow: `backend/app/workflows/create_pmp.py`
- Phase 1 validation fixes: `backend/app/sitewise/pmp_evidence_validation.py`, `pmp_greenfield_brief.py`
