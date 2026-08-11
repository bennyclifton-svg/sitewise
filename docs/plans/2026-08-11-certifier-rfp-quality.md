# Certifier RFP Quality Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Update the Progress checklist after every stage before starting the next.

**Goal:** Make consultant RFPs (starting with Certifier / PCA) issue-ready: numbered citations including Project Profile as `[1]`, correct seed doctrine, certifier-fit fee stages/services/evidence, and identity-conflict surfacing.

**Architecture:** Keep the existing hybrid RFP path (deterministic scaffold in `rfp_renderer.py` + bounded narrative in `rfp_narrative.py` + discipline profiles in `consultant_procurement.py`). Fix provenance and discipline fit in the scaffold/profile/seed layers first; do not rewrite the narrative agent. Prefer reusing existing seeds over inventing a new PCA corpus unless gaps remain after wiring.

**Tech Stack:** Python 3.12, FastAPI backend workflows, pytest. Frontend chip rendering already treats `[n]` correctly; no frontend change required for citations if source cells emit `[n]` only.

**Related:** Builds on `docs/plans/2026-07-22-rfp-quality-and-consultant-status.md` (Part 1 shipped). Triggered by Petersham Certifier RFP v1 review (2026-08-11).

---

## Progress checklist

Update this section after each stage completes.

- [x] **Stage 1 — Citations:** Project Profile as `[1]`; evidence `[2+]`; Citation key section; no `Profile`/`Confirm` chips in summary source column *(done 2026-08-11; `test_rfp_renderer.py` 13 passed)*
- [x] **Stage 2 — Seed routing:** Certifier uses consultant-procurement + PCA/authority guidance; contractor tendering guide demoted/removed for this path *(done 2026-08-11; quoting+setup/commission wired; tendering filtered from consultant RFPs)*
- [x] **Stage 3 — Certifier fee stages + services/deliverables:** PCA-shaped fee table; stronger default services; numbered deliverables *(done 2026-08-11)*
- [x] **Stage 4 — Evidence queries + identity conflicts:** Certifier-biased retrieval; address/client conflicts recorded in Trace & QA *(done 2026-08-11)*
- [x] **Stage 5 — Forecast hygiene:** Prefer certifier-specific cost-plan rows over bundled "Fire engineer and certifier" when separable *(done 2026-08-11)*
- [x] **Stage 6 — Verification:** Targeted pytest green; optional Petersham regen notes *(done 2026-08-11; 133 related tests passed)*

---

## Stage 1 — Project Profile citation `[1]` + Citation key

**Why:** Live Petersham Certifier RFP shows blue `Profile` chips and has no Citation key. User wants profile as numbered source `[1]` and a citations table at the bottom.

**Files:**
- Modify: `backend/app/sitewise/pmp_citations.py` (optional helper for reserved first citation)
- Modify: `backend/app/sitewise/rfp_renderer.py`
- Modify: `backend/tests/sitewise/test_rfp_renderer.py`
- Check: `backend/app/sitewise/artifact_presentation.py` (must not strip/rewrite `[1]` profile lines wrongly)
- Check: `frontend/src/components/project/MarkdownContent.tsx` (already chips `[n]`; leave alone unless regression)

**Design decisions:**
1. Reserve citation slot `[1]` for label `project-profile` (stable path/label, not a real file).
2. Number retrieved project evidence from `[2]` onward via `build_rfp_citation_index`.
3. Project Summary source cells:
   - Profile-backed identity fields (project title when not evidence-matched, site/client when no corroborating doc, state/taxonomy/scale) → `[1]`
   - Evidence-corroborated site/client/title → evidence token `[n]`
   - Budget from cost plan → keep human-readable cost-plan source **or** add cost plan into citation index if already in evidence; do not invent a second chip vocabulary
4. Append `## Citation key` before `## Trace & QA` (issue-facing). Trace & QA remains export-excluded.
5. Citation key lines:
   - `[1] Project Profile — current`
   - `[n] {basename} — on file` for evidence docs
6. Flip existing assertion `assert "## Citation key" not in scaffold` to require the section.

**Tests (TDD):**
- `test_rfp_citation_index_reserves_project_profile_as_one`
- `test_rfp_summary_cites_project_profile_as_one_when_no_corroborating_evidence`
- `test_rfp_scaffold_includes_citation_key_with_profile_first`
- Update `test_rfp_summary_keeps_provenance_in_source_column_without_status_prose` — empty cells for unused rows OK, but profile-sourced rows should be `[1]` not blank/`Profile`
- Keep/adjust `test_rfp_summary_cites_evidence_that_corroborates_profile_identity` for `[2+]` evidence tokens

**Done when:** pytest for `test_rfp_renderer.py` green; scaffold has no `Profile`/`Confirm` source chips; Citation key lists Project Profile as `[1]`.

---

## Stage 2 — Certifier / consultant seed routing

**Why:** Petersham Certifier provenance only loaded `procurement-tendering-guide.md` (contractor commercial tendering) + multi-res cost reference. Wrong doctrine.

**Files:**
- Modify: `data/seed/procurement-tendering-guide.md` frontmatter `required_by` — remove `consultant-procurement` (keep head-contractor / trade / create-pmp as appropriate)
- Confirm: `data/seed/procurement-quoting-guide.md` keeps `consultant-procurement: 1`
- Modify: `backend/app/workflows/consultant_procurement.py` certifier `DisciplineProfile`:
  - `knowledge_paths`: at least
    - `seed/procurement-quoting-guide.md`
    - `seed/setup-and-commission-guide.md` (PCA appointment gates)
    - optionally `seed/ncc-reference-guide.md` only if char budget allows; otherwise rely on query terms
  - `knowledge_query_terms`: principal certifier, PCA, construction certificate, occupation certificate, critical stage inspections, statutory notifications
- Modify: `ConsultantDocument.filter_platform_knowledge` or `platform_guidance_paths` so certifier never surfaces `procurement-tendering-guide.md` even if retrieved by search
- Test: `backend/tests/workflows/test_consultant_procurement.py` (or new focused tests)

**Done when:** Certifier platform guidance paths/tests assert quoting + setup/commission (or PCA terms) present and tendering guide absent.

---

## Stage 3 — Certifier fee stages, services, deliverables

**Why:** Live draft uses designer fee stages (Concept/Detailed design). Services are OK but deliverables still bullets-only in scaffold defaults.

**Files:**
- Modify: `backend/app/sitewise/rfp_renderer.py` — allow discipline-specific fee breakdown via optional hook/table builder
- Modify: `backend/app/workflows/consultant_procurement.py` — certifier profile:
  - Expand `requested_services` (appointment independence, CC/CDC, CSI regime, OC, exclusions of third-party certificates)
  - Expand `deliverables` if needed
- Modify: render path so **Required deliverables** are numbered (`1.` …) like requested services
- Test: renderer + consultant_procurement tests for certifier fee table wording

**Certifier fee stages (target):**
1. Information review / pathway confirmation
2. Construction approval support (CC/CDC)
3. Statutory notifications & appointment administration
4. Critical-stage inspection regime
5. Re-inspection / non-conformance allowances
6. Occupation certificate / completion
7. Optional / additional services
8. Hourly rates / disbursements / authority fees (pass-through)

**Done when:** Certifier scaffold fee table has no Concept/Detailed design rows; deliverables numbered.

---

## Stage 4 — Evidence queries + identity conflicts

**Why:** Retrieval over-weighted access PBDB; background used Parramatta Rd while profile had Queen St.

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py` — certifier `evidence_query_terms` + optional specialty queries for DA/CDC/CC, consent conditions, BASIX, fire safety schedule, inspection
- Modify: `backend/app/sitewise/rfp_renderer.py` and/or assumptions helper — when profile site/client disagree with top evidence snippets, append Trace & QA **Inputs to resolve** / **Working basis** conflict lines (do not silently overwrite profile in summary)
- Test: unit tests with conflicting address evidence

**Done when:** Conflict appears in Trace & QA; summary still shows profile address with `[1]` (or evidence citation if intentionally corroborated); tests cover conflict detection.

---

## Stage 5 — Forecast hygiene

**Why:** Forecast matched bundled cost item "Fire engineer and certifier" at $10k.

**Files:**
- Modify: `backend/app/workflows/consultant_procurement.py` `_forecast_for_discipline` matching — prefer terms that match certifier alone; if only bundled row exists, label clearly as bundled judgement
- Test: forecast unit coverage with bundled vs specific rows

**Done when:** Certifier forecast either hits a certifier-only row or explicitly labels bundled allowance.

---

## Stage 6 — Verification

1. `uv run pytest tests/sitewise/test_rfp_renderer.py tests/workflows/test_consultant_procurement.py -q` (plus any new files)
2. Fix regressions in trade renderer if shared helpers changed
3. Update this Progress checklist to all `[x]`
4. Note for operator: regenerate Petersham Certifier RFP after deploy to validate live output

**Completed verification (2026-08-11):**
- `tests/sitewise/test_rfp_renderer.py`
- `tests/workflows/test_consultant_procurement.py`
- `tests/workflows/test_trade_procurement.py`
- `tests/sitewise/test_catalog_parity.py`
- `tests/sitewise/test_seed_routing.py`
- `tests/sitewise/test_taxonomy_seed_selection.py`
- `tests/sitewise/test_cost_plan_consultant_forecast.py`

Result: **133 passed**.

**Operator follow-up:** Restart/reload the backend if needed, then regenerate the Petersham Certifier RFP to validate live output (Profile → `[1]`, Citation key, PCA fee stages, quoting/setup seeds, address conflict in Trace & QA).

**2026-08-11 follow-up (procurement UX + regen guard):**
- Killed duplicate uvicorn processes; single in-proc worker now loads citation fixes.
- Regenerating a legacy RFP (Profile chips / no Citation key) forces a full scaffold replace so block reconcile cannot preserve the old shell.
- Procurement panel: single **Open** combobox (`Discipline · Type · vN`), create row is Type + Discipline (PMP-backed datalist), no draft badge chips.

**Commits:** Only when the user explicitly asks. Do not auto-commit between stages unless requested.

---

## Out of scope

- Full new PCA seed corpus authoring (reuse existing seeds first)
- Frontend redesign of citation chips
- Auto-filing `_inbox` documents (separate Petersham filing workstream)
- Live consultant-status tracker (still open in 2026-07-22 plan Part 2)
- Regenerating the live Petersham draft inside this coding pass unless asked
