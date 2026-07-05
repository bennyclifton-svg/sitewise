# PMP 2.0 — Phase 6: Live Document Lifecycle at Scale

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13, test commands, recorded baseline test failures. The PMP evidence mandate (2026-07-04) is the governing rule here: **every active document in the current project corpus snapshot must be read and considered**.
> **Depends on:** [Phase 4](04-phase-4-adaptive-pmp.md) and [Phase 5](05-phase-5-interactive-pmp.md). Run last, single agent — this phase integrates the others.

**Outcome:** The PMP behaves as the live document of pmp2.md's framing — from one-line brief to 100-document commercial corpus — with a visible current-corpus sweep. Refresh is based on the active document snapshot, not accumulated upload history: deleted and superseded documents stop supporting future PMP facts.

## Task 6.1: Current active corpus sweep in Update PMP

**Files:**
- Modify: `backend/app/workflows/update_pmp.py` + `create_pmp.py` (shared retrieval helpers)
- Modify: document repository/source-document accessors as needed to expose the active current revision set (deleted rows excluded; superseded revisions excluded unless explicitly retained active)
- Test: `backend/tests/workflows/test_update_pmp_sweep.py`

Changes:
1. Replace the `limit: int = 8` delta with a current active corpus snapshot sweep honouring the evidence mandate: **every active current project evidence document** is considered on refresh. The query must not use `since=baseline.created_at` as the selection boundary for taxonomy PMPs.
2. Define a helper such as `list_current_pmp_corpus_documents(project_slug)` that returns project evidence only, excludes platform knowledge, excludes deleted documents, and excludes superseded revisions unless the user explicitly retained them active. If the current repository model lacks explicit revision status, add the smallest metadata/accessor change needed rather than inferring from filenames.
3. Batch extraction: chunk active docs into groups of ~8 (`CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS`), run `extract_mobilisation_evidence_pack` extraction per batch, merge packs (extend `mobilisation_evidence.py` with `merge_evidence_packs` — union of extracted fields, current-active-doc-wins on conflicts, gaps recomputed after merge; TDD it in `tests/sitewise/test_mobilisation_evidence.py`).
4. Recompute evidence from the current snapshot, then compare to the previous PMP. Facts supported only by deleted/superseded/missing docs are downgraded to `Not evidenced`/`Assumption` unless user-authored, in which case they remain user-authored with a visible evidence-status warning.
5. Emit a trace event per batch (`step="evidence_sweep"`, metadata: batch index, active doc names, skipped deleted/superseded counts) so the ActivityFeed shows the sweep happening.
6. Guardrail: cap total swept active docs at a config setting (`backend/app/config.py`, e.g. `pmp_sweep_max_documents = 150`) with a trace warning if exceeded.

## Task 6.2: Sweep trigger + change summary UX

**Files:**
- Modify: `backend/app/workflows/update_pmp.py` — provenance_metadata gains `sections_changed: list[str]` (heading-level diff vs baseline, deterministic), `evidence_changed: {added, removed, superseded, downgraded, conflicted}` summary, and seed section refs loaded.
- Modify: `frontend/src/components/project/DraftReviewPanel.tsx` / `ActivityFeed.tsx` — "Refresh PMP from documents" action (existing update endpoint), a "What changed in v{n}" strip listing `sections_changed`, and a compact evidence-change strip (added/removed/superseded/conflicts) linking to the trace.
- Tests both sides.

## Task 6.3: Minimal-brief path regression hardening

**Files:** `backend/app/workflows/create_pmp.py`, fixtures in `backend/tests/workflows/`.
Phase 4 owns the first implementation of the zero-document scaffold (D8). This task hardens it at lifecycle scale: Create PMP and Refresh PMP both preserve the base-case scaffold when the active corpus is empty, and a project that previously had documents but now has none downgrades formerly grounded rows. Fixture test: `residential / new / house / budget $1M` from title+taxonomy alone — asserts decision-block count ≥ 4, no `Grounded` claims, `User provided` for the budget/profile fields, lightweight annexures/checklists exist, and `pmp_min_words ≤ pmp_word_count(primary_view) ≤ pmp_max_words * 1.05`.

## Task 6.4: Scale + regression evals

**Files:** `backend/tests/workflows/test_pmp_scale.py` (synthetic 100-doc active corpus fixture — small docs, no LLM in the loop for the batching/merge logic tests); re-run the Phase 4 matrix fixtures end-to-end; record a manual live-eval checklist in `docs/pmp2.0/pmp2-acceptance.md` (Benny's sign-off doc: one no-document base case, one residential refurb, one commercial new, one commercial fire-services refurb, one advisory, one 100-doc sweep, one deleted/superseded evidence downgrade — each checked in print preview: **within the 2–4 A4 primary page band**, emphasis lands on the right sections, annexures preserve overflow detail).

## Definition of done

All backend/frontend suites green (minus recorded baseline); acceptance doc written; live smoke on the caves-beach-reno project (existing corpus) shows v(n+1) PMP with current-active-corpus sweep trace, preserved user decisions, evidence downgrades for removed sources, and annexure links for overflow detail.
