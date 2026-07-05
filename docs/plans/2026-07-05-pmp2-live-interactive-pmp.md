# PMP 2.0 — Live Interactive PMP, Full Class Matrix, and Subclass/Scale/Complexity Taxonomy

> **For Claude:** This is the **shared-context overview** for the PMP 2.0 work — required reading for every implementing agent, but it contains no tasks. Implementation lives in the phase documents under [pmp2/](pmp2/) (index below); each is independently hand-off-able and uses superpowers:executing-plans.

**Goal:** Turn the PMP from a static markdown artifact into a live, semi-interactive, **2–4 page** document that spans the full Australian construction matrix (6 building classes × 5 work types, with subclass/scale/complexity), continuously refreshed by document sweeps over the current active project corpus, with section depth adapting to project type and risk profile. The product must work at both ends of the spectrum: a one-line/taxonomy-only project with no uploaded documents, and an evidence-rich project with up to ~100 active uploaded documents.

**Architecture:** Markdown stays the canonical draft format (preserving the entire existing validation/versioning/provenance pipeline); interactivity is added via typed, fenced `pmp-decision` blocks embedded in the markdown, rendered as widgets by the existing react-markdown pipeline and persisted to a new `project_decisions` table. Taxonomy (class/type/subclass/scale/complexity/risk-flags) is declarative JSON config under `data/taxonomy/`, loaded by a deterministic backend module (same pattern as `knowledge_catalog.py`), driving the project-setup UI, seed/section selection, and the emphasis profiles that budget each PMP section's depth. The `data/seed-commercial/` guides are normalised into the existing frontmatter-driven knowledge catalog, and PMP generation loads curated seed **sections** deliberately for each PMP section rather than leaning on the model's pretrained domain knowledge. The visible PMP carries compact evidence-status chips; the detailed sweep, seed sections, and validation trace live in the existing ActivityFeed/WorkflowTrace infrastructure.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), pydantic-ai agents (generation), React + react-markdown + remark-gfm + TanStack Query (frontend), pytest + vitest.

**Source spec:** `docs/pmp2.0/pmp2.md` (Benny's brief, 2026-07-05). The subclass/scale/complexity tables and NEW/ADVISORY work-scope JSON in that file are the **source data** for the taxonomy config tasks — transcribe from there, improving/tightening as instructed in the spec.

---

## Phase index

| Phase | Document | Depends on | Parallel-safe with |
|---|---|---|---|
| 1 — Taxonomy foundation (backend) | [pmp2/01-phase-1-taxonomy-foundation.md](pmp2/01-phase-1-taxonomy-foundation.md) | — (lands first) | — (blocks all) |
| 2 — Project setup UX (frontend) | [pmp2/02-phase-2-project-setup-ux.md](pmp2/02-phase-2-project-setup-ux.md) | 1 | 3, 4, 5 |
| 3 — Knowledge layer expansion | [pmp2/03-phase-3-knowledge-expansion.md](pmp2/03-phase-3-knowledge-expansion.md) | 1 | 2, 5 |
| 4 — Adaptive 2–4 page PMP | [pmp2/04-phase-4-adaptive-pmp.md](pmp2/04-phase-4-adaptive-pmp.md) | 1, 3 | 2, 5 |
| 5 — Interactive PMP (Objective 1) | [pmp2/05-phase-5-interactive-pmp.md](pmp2/05-phase-5-interactive-pmp.md) | 1 | 2, 3, 4 |
| 6 — Live document lifecycle at scale | [pmp2/06-phase-6-live-document-lifecycle.md](pmp2/06-phase-6-live-document-lifecycle.md) | 4, 5 | — (run last) |

```
Phase 1 (taxonomy backend)  ──┬──▶ Phase 2 (project setup UX)
                              ├──▶ Phase 3 (knowledge merge) ──▶ Phase 4 (2–4 page adaptive PMP)
                              └──▶ Phase 5 (interactive PMP)
Phase 4 + Phase 5 ──▶ Phase 6 (live sweep + scale + evals)
```

**Hand-off rules:**
- Phase 1 must land first. After it, Phases 2, 3→4, and 5 are independent tracks — safe for three agents in parallel (worktrees recommended, see superpowers:using-git-worktrees).
- Phase 6 integrates and hardens; single agent, run last.
- Every phase ends green: its own tests pass, legacy tests pass (minus the recorded baseline failures below), lint clean, work committed in small conventional commits (`feat(taxonomy): …`, `feat(pmp-decisions): …`).
- Agents read: this overview, their phase document, `docs/pmp2.0/pmp2.md`, and the files their phase names. Follow @superpowers:test-driven-development — tasks are structured red→green→commit even where steps are compressed.
- Migration numbering in the phase docs (018, 019) is indicative — **take the next free number** at implementation time; phases may land out of order.

---

## 1. Current state (verified 2026-07-05, branch `feature/omnigent-shell`)

| Concern | Where it lives today | What changes |
|---|---|---|
| Project taxonomy | `projects.archetype` (5 values: new-dwelling, renovation, multi-dwelling, ancillary, small-commercial) + `user_role` (4 roles) + `state`; `Archetype` Literal in `backend/app/sitewise/pmp_sources.py:8` | New `building_class` + `work_type` columns; subclass/scale/complexity in `project_metadata` JSONB; archetype retained only as compatibility/test-fixture fallback, not a product migration target |
| Seed selection | Frontmatter-driven catalog `backend/app/sitewise/knowledge_catalog.py` over `data/seed/*.md`; output pinned by `backend/tests/sitewise/test_catalog_parity.py`; catalog already exposes section IDs and targeted section loading | New frontmatter keys `applies_to_classes` / `applies_to_work_types`; class-aware selection with archetype fallback for tests/compatibility; PMP section -> seed section routing; parity test extended enough to protect existing behavior, but no user-facing legacy migration work |
| Commercial knowledge | `data/seed-commercial/*.md` (10 guides, **different frontmatter schema**: domainSlug/domainType/tags; 5 filenames collide with `data/seed/`) | Merge/normalise into `data/seed/` catalog schema |
| PMP generation | `backend/app/workflows/create_pmp.py` + `update_pmp.py`; pydantic-ai agent, instructions in `create_pmp_instructions.md`; section contracts per role in `pmp_sources.py` (`ROLE_SECTION_HEADINGS`); greenfield contract in `pmp_greenfield_brief.py`; deterministic scaffold in `pmp_renderer.py`; evidence fidelity in `pmp_evidence_validation.py` | Taxonomy projects get a universal **2–4 page** scaffold-first skeleton whose section depth is steered by emphasis profiles; no-document PMPs are first-class outputs; word-band validation covers the primary view; agent emits decision blocks; validation preserves user-locked decisions; legacy archetype generation is test-only compatibility, not a product path to migrate |
| Document sweep | `retrieve_project_evidence_delta` (`create_pmp.py:410`) — docs updated since baseline, limit 8; evidence mandate (2026-07-04): every corpus doc passes through `extract_mobilisation_evidence_pack` | Refresh sweeps the current active corpus snapshot, not only deltas; deleted/superseded documents are not carried forward; scale to ~100-doc corpora via batched extraction; sweep-triggered update UX |
| Draft storage/render | `draft_artifacts.content_markdown`; PATCH `/projects/{id}/drafts/{id}`; accept endpoint; frontend `DraftReviewPanel.tsx` renders via `MarkdownContent.tsx` (react-markdown + remark-gfm); editing = whole-document textarea | Decision-block widgets in `MarkdownContent`; decision PUT endpoint; section-level editing |
| Migrations | Latest is `backend/alembic/versions/017_project_activity_events.py` | 018 (taxonomy columns), 019 (project_decisions) — indicative numbers |

**Pre-existing test failures (do NOT chase these):** `tests/test_chat_api.py` thread CRUD ×3 and `tests/inbox/test_upload.py` fail with `AttributeError` in `app/database/stripe_billing.py:86` (in-flight Stripe work); tender worker Postgres-concurrency integration tests are flaky. Baseline recorded 2026-07-04.

**Commands:**
- Backend tests: `cd backend && uv run pytest tests/sitewise tests/workflows -v` (scope per task)
- Migrations: `cd backend && uv run alembic upgrade head`
- Frontend tests: `cd frontend && npm run test` (vitest)
- Lint: `cd backend && uv run ruff check app tests` / `cd frontend && npm run lint`

---

## 2. Design decisions (for Benny's review — each reversible at plan-approval time)

**D1 — Markdown stays canonical; interactivity via fenced `pmp-decision` blocks.**
The whole pipeline (evidence validation, section-heading contracts, sanitisation, versioning, workspace file export, activity provenance) operates on markdown. A structured-JSON document model would be a rewrite of all of it. Instead the agent/renderer emits fenced blocks (```` ```pmp-decision ````) carrying a typed JSON payload; react-markdown renders them as interactive widgets; everything else keeps seeing markdown. Markdown export simply renders the selected option as text.
*Alternative considered:* full block-based JSON document model → rejected for this iteration (rewrite cost, loses the tested markdown contracts). Revisit only if decision blocks prove insufficient.

**D2 — User selections persist in a `project_decisions` table AND are re-stamped into every future draft.**
A decision the user has made (`source: "user"`) is locked: `update_pmp` injects it as a constraint, and a deterministic post-generation re-stamp guarantees the regenerated draft carries it regardless of what the model did. This also converges with the deferred "decision-register-as-memory" roadmap item — the table is the register.

**D3 — Taxonomy is declarative JSON config in `data/taxonomy/`, not code.**
Same philosophy as the knowledge catalog ("deterministic Python over declarative metadata"). Frontend loads options from a new API endpoint; nothing is hardcoded in components. The spec's tables (pmp2.md §3.2, complexity dimensions, risk flags, work scopes §5) are transcribed into these files.

**D4 — `building_class` and `work_type` become columns; subclass/scale/complexity live in `project_metadata` JSONB.**
Columns for the two axes that drive seed/section selection and filtering; JSONB for the long tail (per-subclass scale fields vary wildly — schema churn in columns would be constant). `archetype` is retained only so existing tests/fixtures and transitional code do not break. There is no product requirement to update old projects: they are test projects only. New user-facing PMP work should start from taxonomy fields.

**D5 — `data/seed-commercial/` merges into `data/seed/` under the catalog frontmatter schema.**
One canonical seed directory, one selection mechanism. The 5 colliding filenames (cost-management-principles, contract-administration-guide, program-scheduling-guide, ncc-reference-guide, as-standards-reference) require a content merge — the commercial versions are richer in commercial content; merged file must keep everything residential PMPs rely on for tests and eval fixtures, but do not spend product effort on legacy project migration.

**D6 — ADVISORY shares the universal skeleton with label variants, not a separate contract.** *(amended after D7 landed)*
Advisory engagements have no mobilisation/construction posture, but under the universal skeleton (D7) they don't need a wholly separate contract — the skeleton swaps two headings ("Procurement & delivery" → "Services & deliverables"; "Programme & milestones" → "Programme of services") and uses an advisory emphasis profile. The document title stays distinct ("Advisory Services Plan").

**D7 — The PMP is a 2–4 page adaptive document: fixed skeleton, weighted depth (Benny, 2026-07-05).**
Every PMP shares one compact skeleton — a **Project Snapshot** metadata block (site, address, client, class/type/subclass, scale, budget, timeframes, procurement route) followed by the **same core section headings** for every project — but the depth of each section is allocated by an **emphasis profile** derived from (building class, work type, work scope, risk flags). A residential new build spends its budget on Scope & Client Requirements (finishes, kitchen/bathroom, fixtures, user wants); a commercial fire-services upgrade spends it on Compliance & Approvals (AS 2419.1 hydrant systems, AS 2941 pumpsets, DtS pathway, essential safety measures). Enforcement is deterministic, not vibes: a word band (config `pmp_min_words`/`pmp_max_words`, defaults 800/1800 ≈ 2–4 A4 pages — calibrate against the print stylesheet during implementation) plus per-section budgets from the profile, validated post-generation with the existing retry-with-feedback loop. Registers (risks, actions/decisions) appear **condensed** inside the band (top ~8 rows); full registers become companion artifacts on the existing draft/workspace infrastructure.
*Alternative considered:* keep long-form documents and render a short summary view → rejected: two documents drift apart; the PMP itself is the 2–4 pager.
*Consequence:* the long-form role contracts in `pmp_sources.py` may remain for compatibility/test fixtures, but they are not a user-facing path to preserve or migrate. New taxonomy projects always get the adaptive contract.

**D8 — The empty-corpus base case is a first-class happy path, scaffold-first.**
A taxonomy project with zero uploaded documents must still produce a useful PMP immediately. The backend deterministically assembles the skeleton, evidence-status rows, seed/doctrine checklists, expected consultants/approvals, open decisions, and lightweight annexures from project setup input + taxonomy + curated seeds. The model may polish wording and prioritise within the supplied contract, but it must not invent domain content outside user input, taxonomy, doctrine, and loaded seed sections. User-entered setup/chat facts are labelled `User provided`, not `Grounded`; missing project files are labelled `Not evidenced` or `Assumption`.

**D9 — Refresh uses the current active corpus snapshot, not accumulated history.**
Update PMP re-sweeps the active project corpus each run, batched and capped for scale. Deleted documents, archived files, and superseded revisions that are no longer active do not support future PMP facts. Facts supported only by removed evidence are downgraded to `Not evidenced`/`Assumption` on the next refresh unless explicitly retained as user-authored judgement; even then, the evidence status must say the current corpus no longer supports it. This replaces the "delta since baseline" mental model for taxonomy PMPs.

**D10 — Evidence status is visible in the PMP and linked to the existing activity trace.**
The PMP shows compact provenance/status labels (`User provided`, `Grounded`, `Partial`, `Assumption`, `Not evidenced`, `Conflict`). The detailed explanation stays in the existing `WorkflowTraceEvent`/ActivityFeed path: sweep batches, active/deleted/superseded document counts, seed section IDs loaded, validation warnings, and changed sections. No second audit-log system.

**D11 — Details overflow into linked or collapsed annexures, not the primary 2–4 pages.**
The primary PMP remains the concise control document even for 100-document projects. Full risk/action/decision/evidence/compliance/consultant detail is preserved in companion artifacts or collapsed annexures linked from the PMP. Annexure rows are generated from deterministic evidence packs, user decisions, and seed-derived registers; the model may summarise but must not be the source of record.

**D12 — Curated seeds and doctrine are the authoritative domain substrate.**
Residential and commercial seed files are treated as the source of domain content. Frontmatter decides which files apply; section-level routing decides which seed sections are loaded for each PMP section. Required seed files/sections must be ingested and present or generation blocks with a trace message. Optional enrichment sections may warn and continue. General pretrained domain knowledge must not fill PMP content gaps; if the curated seeds do not cover something material, output a gap/judgement for user confirmation instead of inventing coverage.

**D13 — User intent wins silently nowhere.**
User-locked decisions and user-edited wording survive regeneration, but conflicts with current corpus evidence are visible. If evidence suggests a different procurement route, taxonomy, approval path, or programme basis, the PMP keeps the user selection, marks it as user-selected, and creates a conflict/action row. Uploaded documents may suggest taxonomy/profile changes; they must not silently change class/type/subclass because that would alter seed selection and section weighting.

---

## Deferred / out of scope (recorded so agents don't scope-creep)

- **Cost plan expansion** beyond residential (`cost_plan_sources.py` gate untouched) — needs commercial cost reference data first.
- "Other"-selection pattern analysis for AI learning (spec §3.2 rules) — we store the free text; analysis is future work.
- Free-form rich-text (non-section) editing, comment threads, multi-user concurrency on decisions.
- Infrastructure-class deep content (authority interface libraries, corridor access seeds) — section skeleton lands, knowledge depth grows later.
- The spec's `agricultural` complexity block — folded into industrial/infrastructure dimensions (see Phase 1 Task 1.1 note); a dedicated agricultural class is not in the six-class matrix.

## Open items for Benny at plan review

Resolved during alignment review on 2026-07-05: D1 markdown + decision blocks, D6 advisory label variants, D7 2–4 page primary view, condensed inline registers with full companion annexures, D8 empty-corpus first-class scaffold, D9 active-corpus refresh semantics, D10 trace linkage, D11 annexures, D12 seed-section authority, D13 conflict handling, and the legacy-project stance: old archetype projects are test fixtures only and do not need migration.

Remaining items:

1. The 24 seed `summary:` fields from the 2026-07-04 restructure were still awaiting your review; Phase 3 adds ~10 more — same review batch?
2. Phase ordering: knowledge/matrix (3–4) before interactive (5) is the written order, but they're parallel tracks — if you want Objective 1 visible first, run Phase 5 with a second agent from day one.
3. Review the seeded emphasis-profile weights (Phase 1 Task 1.1, `emphasis-profiles.json`) — the residential-scope-heavy / commercial-refurb-compliance-heavy defaults encode your 2026-07-05 guidance; the per-combo table is yours to tune.
