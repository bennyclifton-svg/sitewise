# TCM M3–M6 Handoff Package — Overview

- **Date:** 2026-06-13
- **Prepared by:** planning session (frontier model); execution intended for a cost-effective coding model
- **Governing spec:** `docs/plans/2026-06-11-tender-comparison-module-prd.md` (the PRD). **The PRD wins every disagreement.**
- **Binding rules:** AGENTS.md → "Tender Comparison Module (TCM)" section.

## State of play (verified 2026-06-13)

The TCM codebase is currently **split across two locations**:

| Where | What | Status |
| --- | --- | --- |
| Branch `feature/tcm-m1-skeleton` (worktree `.worktrees/tcm-m1`) | Migrations 007–010, full §8 models (19 tables, 621 lines), `tender_jobs` queue with SKIP LOCKED, worker w/ handler registry, `services/ingestion.py` (stub-level), tests | **Committed** (11 commits on top of `b1c6f03`) |
| Main working tree (branch `feature/cost-plan-quality-fixes`) | `data/tender/` seeds, `seeds/load.py`, `llm/` (client protocol + OpenAI impl + extraction prompt v0.1.0), `services/extraction.py` (reconciliation + confidence gating), `eval/` (golden loader, metrics, harness), 8 test files, **its own 151-line `models.py`** (5 knowledge tables only, plus a `report_language` table the M1 branch does *not* have) | **Untracked — never committed** |

Consequences:

- **Stage 0 (consolidation) is mandatory before M3.** See `01-stage0-consolidation.md`.
- The eval `metrics.py` already counts mapping pairs and silence classes — M3/M4 only need `PredictionRunner` implementations, not new metric code.
- No embedding storage exists for taxonomy synonyms (checked migration 008). M3 adds migration 011.
- `services/ingestion.py` on the M1 branch is a stub (single function, no OCR/render imports). PRD §7.4 ingestion may be incomplete — Stage 0 audits this and the gap, if real, becomes Stage 0.5.

## Stage map

| Stage | Doc | PRD anchors | Sessions |
| --- | --- | --- | --- |
| 0 — Consolidation | `01-stage0-consolidation.md` | §7.1, §8 | 1 |
| M3 — Mapping cascade | `02-m3-mapping.md` | §9.3, §7.5, §14 | 1–2 |
| M4a — Expectations + silence | `03-m4-expectations-silence.md` | §9.4, §9.5, App A/B/C | 1 |
| M4b — Analysis + flags | `03-m4-expectations-silence.md` (Part B) | §9.6, §9.7 | 1 |
| M5a — API + report pipeline | `04-m5-qa-console-report.md` (Part A) | §9.8, §13, §15 | 1 |
| M5b — QA console frontend | `04-m5-qa-console-report.md` (Part B) | §12, §16 | 1–2 |
| M6 — Pilot | `05-m6-pilot-runbook.md` | §19, §11.3, §18 | human-led |

## Session protocol (apply to every implementation session)

1. One stage (or named part) per session. `/clear` between sessions.
2. Session must start by reading: AGENTS.md TCM section, the named PRD sections, and the stage doc. Nothing else until a short plan is echoed back.
3. TDD: failing test → minimal code → green → commit. Commit after **every** green step.
4. No file outside the stage doc's file list may be created or modified. If the model believes it must, it stops and reports why instead.
5. "Done" requires pasted test output (`uv run pytest backend/tests/tender -q`) and, where migrations are touched, an upgrade→downgrade→upgrade roundtrip output.
6. Any conflict between the model's idea and the PRD: say "check that against PRD §X". The spec wins.
7. Prompts/model config/taxonomy/rule changes require an eval run attached (PRD §14) — from M3 onward the harness exists; use it.

## Invariants the implementing model must never violate

- LLMs classify and map; **all arithmetic is Python** (PRD §7.5).
- Money is integer cents, end to end. No floats for currency.
- Report language only from `data/tender/report_language.yaml` / Appendix C. "Excluded" requires an explicit page-referenced exclusion. Silence-path `excluded` outcomes are always downgraded to `silent_ambiguous` + QA (App B).
- Every LLM output row records `{model, prompt_version, request_id}`. Prompts are versioned files in `backend/tender/llm/prompts/`.
- One-way dependency: `backend/tender/` may import `app.*`; no Clerk core module imports `tender.*`.
- Stages are idempotent and re-runnable; human QA decisions (`tier=human`, `qa_state in (confirmed, corrected)`) are never overwritten by a re-run.
- Confidence thresholds are config keys, never literals: existing keys plus the new ones named in each stage doc.

## What NOT to delegate to the cheap model

- **Stage 0 merge review** — the model executes the steps; Ben reviews the diff before the consolidation commit is pushed.
- **Golden-set annotation** (real quote ground truth) — human.
- **QS red-pen day** (PRD §11.3) — human, blocking before any customer report.
- **Benchmark calibration judgment and report tone/§13 copy** — Ben reviews every word in the template the first time.
- **Eval-gate verdicts** — the model runs `pytest -m tender_eval` and reports numbers; Ben decides pass/fail on regressions.

## Paste-ready session prompts

### Stage 0

```
Read AGENTS.md ("Tender Comparison Module" section), PRD sections 7-8
(docs/plans/2026-06-11-tender-comparison-module-prd.md), and
docs/plans/tcm/01-stage0-consolidation.md in full. Execute the stage doc
exactly: consolidate the TCM work from branch feature/tcm-m1-skeleton and the
untracked files in the working tree onto a single branch feature/tcm-main,
following the reconciliation rules in the doc. Do not redesign anything.
Finish by pasting: full pytest output for backend/tests/tender, the alembic
upgrade/downgrade/upgrade roundtrip output, and `git log --oneline` of the new
branch. Stop and ask before any destructive git operation.
```

### M3 — mapping

```
Read AGENTS.md (TCM section), PRD sections 9.3, 7.5 and 14, and
docs/plans/tcm/02-m3-mapping.md in full. You are implementing milestone M3
only, on branch feature/tcm-main. Echo back a numbered task list matching the
stage doc before writing code. TDD throughout; commit after every green step;
thresholds go in config keys named in the stage doc, never inline literals.
LLM calls must be mockable — unit tests never hit the network. Finish with
full pytest output and the eval-harness baseline numbers as described in the
stage doc's exit criteria.
```

### M4a — expectations + silence

```
Read AGENTS.md (TCM section), PRD sections 9.4, 9.5, Appendix A, B and C, and
docs/plans/tcm/03-m4-expectations-silence.md Part A in full. Implement Part A
only on feature/tcm-main: the deterministic expectation engine and silence
inference. The expectation engine takes ONLY ProjectContext as input — no
document data, no LLM. Silence inference assembles the Appendix B evidence
packet deterministically before its single adjudication call per cell, and an
`excluded` outcome from that path is ALWAYS downgraded to silent_ambiguous +
needs_review. TDD; commit per green step; finish with full pytest output.
```

### M4b — analysis + flags

```
Read AGENTS.md (TCM section), PRD sections 9.6, 9.7, 13 and 18, and
docs/plans/tcm/03-m4-expectations-silence.md Part B in full. Implement Part B
only on feature/tcm-main: gap matrix, true-comparable-price ledger, allowance
realism, cross-quote outliers, flags and the question list. Everything in this
part is deterministic Python — zero LLM calls. All money in integer cents.
Claim strength is capped by benchmark confidence exactly per PRD 9.7. Use
table-driven unit tests with hand-computed expected values. Finish with full
pytest output.
```

### M5a — API + report

```
Read AGENTS.md (TCM section), PRD sections 9.8, 13, 15 and 18, and
docs/plans/tcm/04-m5-qa-console-report.md Part A in full. Implement Part A
only on feature/tcm-main: the /api/tender router per PRD section 15, the QA
queue/resolve endpoints (every resolve writes tender_corrections; mapping
corrections also insert a taxonomy_synonyms row), and report assembly
(Jinja2 -> HTML -> WeasyPrint PDF) through Clerk's draft lifecycle. Narrative
blocks are operator-editable; tables regenerate from data and are never
hand-edited. Pre-approval renders are watermarked DRAFT. TDD; commit per green
step; finish with full pytest output.
```

### M5b — QA console frontend

```
Read AGENTS.md (TCM section), PRD sections 12 and 16, and
docs/plans/tcm/04-m5-qa-console-report.md Part B in full. Implement Part B
only on feature/tcm-main: cockpit routes per PRD section 16, the three-pane
QA console with keyboard bindings (a/e/j/k/s), page-image viewer with bbox
overlay (images + coordinates only, no PDF.js text layer), and the virtualised
comparison matrix. Follow the existing frontend conventions in
frontend/src/components/project/. Finish with the frontend build and test
commands passing, output pasted.
```

### M6

M6 is a human-led runbook (`05-m6-pilot-runbook.md`), not a coding session.
Use ad-hoc small sessions for the punch-list items it generates.

## Verified local commands (Stage 0, 2026-06-13)

All commands run from `backend/` (not the repo root — the stage-doc forms
`uv run pytest backend/tests/tender -q` etc. do not resolve from the root):

```bash
cd backend
uv run pytest tests/tender -q                 # full TCM suite (56 passed)
uv run alembic upgrade head                   # migration chain incl. 011
uv run alembic downgrade 010_tender_jobs_eval # roundtrip down (full revision id, not "010")
uv run python -m tender.seeds.load            # seed load; second run reports "Total: 0 changed"
```

The seed validator runs from the repo root:

```bash
python data/tender/tools/validate.py
```

Notes:

- `backend/.env` must exist (copy from the main checkout or `.env.example`) —
  `Settings` requires `database_url` and `openai_api_key` even at test-collection time.
- The integration migration test is `pytest -m integration tests/tender/test_migrations.py`;
  it walks the chain down to `006_cockpit_refresh_indexes` and drops tender-table data.
