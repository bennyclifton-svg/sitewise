# PMP 2.0 — Phase 4: Adaptive 2–4 Page PMP for the Full Matrix

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13 (D6-D13 are the contract for this phase), test commands, recorded baseline test failures.
> **Depends on:** [Phase 1](01-phase-1-taxonomy-foundation.md) and [Phase 3](03-phase-3-knowledge-expansion.md). **Parallel-safe with:** Phases 2, 5.

**Outcome:** Create/Update PMP produces a **2–4 page** primary document with one universal skeleton whose section depth follows the emphasis profile (D7): residential new builds read scope/finishes-heavy, commercial fire upgrades read compliance-heavy (naming the actual AS references — hydrants AS 2419.1, pumpsets AS 2941). Empty-corpus taxonomy projects are scaffold-first and useful from title/taxonomy/user inputs alone (D8). Complexity/risk flags feed a condensed risk register. Overflow detail is preserved in companion annexures (D11). Legacy archetype projects are test fixtures only; keep compatibility if cheap, but do not build migration/update behavior for them.

## Task 4.1: Universal section skeleton

**Files:**
- Create: `backend/app/sitewise/section_contracts.py`
- Modify: `backend/app/sitewise/pmp_sources.py` — `required_section_headings(user_role)` grows optional `work_type`/`building_class` kwargs and delegates. Taxonomy calls use the universal skeleton; no-taxonomy legacy calls may continue to resolve to today's tuples for tests/transitional compatibility.
- Test: `backend/tests/sitewise/test_section_contracts.py`

Design — one skeleton, not per-role/per-class trees. Display headings map 1:1 to the `PMP_CORE_SECTIONS` ids from `emphasis-profiles.json`, with per-work-type label variants (D6):

```python
PMP_SECTION_HEADINGS: dict[str, str] = {
    "snapshot": "Project snapshot",                      # metadata table: site, address, client,
    "scope-client-requirements": "Scope and client requirements",  # class/type/subclass, scale, budget,
    "compliance-approvals": "Compliance and approvals",  # timeframes, procurement route, status
    "programme": "Programme and milestones",
    "cost-budget": "Cost and budget",
    "procurement-delivery": "Procurement and delivery",
    "risks": "Risks and mitigations",
    "actions-decisions": "Actions and decisions",
}
WORK_TYPE_HEADING_VARIANTS: dict[str, dict[str, str]] = {
    "advisory": {
        "procurement-delivery": "Services and deliverables",
        "programme": "Programme of services",
    },
}

def pmp_section_headings(*, work_type: str | None) -> tuple[str, ...]: ...
def document_title(user_role: str, work_type: str | None) -> str:
    """advisory -> 'Advisory Services Plan'; otherwise today's role titles."""
```

Dispatch rule (tested): `effective_taxonomy(project).building_class` present → universal skeleton; NULL → legacy `ROLE_SECTION_HEADINGS` tuple for compatibility only. Tests pin: universal skeleton identical across classes; advisory label swaps; unknown work_type falls back to base labels; one light legacy tuple regression is enough.

## Task 4.2: Emphasis-weighted greenfield contract + prompt

**Files:**
- Modify: `backend/app/sitewise/pmp_greenfield_brief.py` — `build_greenfield_brief` receives the project's taxonomy, user-provided setup fields, section weights, and routed seed section refs. The content contract becomes budget-annotated: each section line reads like `"Compliance and approvals (~{int(weight * target_words)} words): cover DtS pathway, essential safety measures, and the specific AS references from seed/as-standards-reference.md#fire-services and the selected work scope"`, where `target_words = (pmp_min_words + pmp_max_words) // 2`. It also carries: subclass scale summary line (for the snapshot table), selected complexity options with uplift labels, derived risk flags, selected work-scope items with consultant lists from `work-scopes.json`, and user-provided fields labelled as `User provided`.
- Modify/Create deterministic scaffold support in `backend/app/sitewise/pmp_renderer.py` (or a small adjacent module if cleaner) so taxonomy `platform_seeded` PMPs are assembled scaffold-first. The scaffold includes the universal sections, compact evidence-status rows, expected consultant/approval/checklist rows from loaded seeds, open decisions, and top risk/action rows. Every project-specific fact with no current evidence is `User provided`, `Assumption`, or `Not evidenced`; never `Grounded`.
- Modify: `backend/app/workflows/create_pmp.py` / `create_pmp_instructions.md` — prompt includes a "Project taxonomy" block, per-section word budgets, and "Loaded seed sections" with `path#section_id` refs. Instructions rewrite for taxonomy projects: **length discipline** (the primary document is 2–4 A4 pages; budgets are guides — spend up to a section's budget where the project warrants it, and cut generic prose before cutting project-specific facts), condensed registers (top ~8 risks, top ~8 actions/decisions — full registers are companion artifacts/annexures), cite specific AS/NCC references from supplied seed sections instead of generic compliance prose, snapshot metadata as a compact table, and no fallback to pretrained domain content where a required seed section is missing. Existing long-form scaffold rules can remain for no-taxonomy tests, but are not a product path.
- Modify: `backend/app/sitewise/pmp_renderer.py` — `_baseline_risk_rows` union with rows derived from risk flags (`derive_risk_flags` → one row each, status "Assumption", mitigation from the flag description), then **cap at 8 rows** ranked by severity (critical > warning > info) for taxonomy projects. Do not spend effort making legacy/no-taxonomy renderer paths byte-identical beyond existing test compatibility.
- Tests: `backend/tests/sitewise/test_greenfield_taxonomy.py` (budget annotations present and sum ≈ target words; fire_services scope contract line names AS 2419.1/AS 2941 seed section refs), a taxonomy `platform_seeded` fixture from title+taxonomy only (all headings, `User provided`/`Assumption`/`Not evidenced`, no `Grounded`, decision-block count ≥ 4), extend `backend/tests/sitewise/test_mobilisation_evidence.py` only if pack surface changes.

## Task 4.3: Deterministic length validation

**Files:**
- Create: `backend/app/sitewise/pmp_length.py`
- Modify: `backend/app/config.py` — `pmp_min_words: int = 800`, `pmp_max_words: int = 1800` (≈ 2–4 A4 pages; calibrate once against the Phase 5 print stylesheet and record the calibration in the commit message).
- Modify: `backend/app/workflows/create_pmp.py` + `update_pmp.py` — fold length violations into the existing validation/retry-with-feedback loop (taxonomy projects only).
- Test: `backend/tests/sitewise/test_pmp_length.py`

```python
def pmp_word_count(markdown: str) -> int:
    """Words as rendered in the primary PMP view: tables count cell text;
    pmp-decision fences count only the selected option's label (that's what
    renders); linked/collapsed annexure content is excluded from the primary
    2-4 page band; code fences otherwise counted verbatim."""

def length_violations(
    markdown: str, *, weights: dict[str, float], min_words: int, max_words: int
) -> list[str]:
    """Total > max_words * 1.05 -> hard violation naming the overshoot.
    Total < min_words -> violation telling the model which (highest-weighted)
    sections to deepen with project-specific content.
    Any section > weight * max_words * 1.5 -> violation naming the section
    and its target, so the retry feedback tells the model where to cut."""
```

Tests: word count stable across decision restamps; per-section attribution uses the same `##` splitting contract as `markdown_sections.py`; violation messages actionable ("Compliance and approvals is 620 words, budget ~330 — condense"; "Draft is 540 words, minimum 800 — deepen Scope and client requirements").

## Task 4.4: Validation + gap handling for non-residential

**Files:**
- Modify: `backend/app/sitewise/pmp_evidence_validation.py` — add taxonomy-aware provenance validation: `Grounded` is forbidden in `platform_seeded`; user setup facts may be `User provided`; current-corpus facts may be `Grounded`/`Partial`; missing required evidence stays `Not evidenced`/`Assumption`; conflict rows are allowed and expected when user locks disagree with evidence. Add regression tests that commercial/advisory drafts pass `evidence_grounded_violations` and structure checks (the heading validator must use the skeleton from Task 4.1).
- Modify: `backend/app/workflows/create_pmp.py` + `update_pmp.py` — everywhere `required_section_headings(user_role)` / `document_title_for_role` is called, pass work_type/class from `effective_taxonomy`.

## Task 4.5: Matrix eval fixtures

**Files:** follow the existing eval/fixture pattern under `backend/tests/sitewise/` (see how greenfield/renovation fixtures are structured — e.g. `test_builder_quote_evidence.py` and pmp fixture tests).
Minimum fixtures: (residential, new, architect-pm, title+taxonomy only, no documents) — base case; (residential, refurb, architect-pm, taxonomy path); (commercial, new, architect-pm, subclass office + complexity live_environment); (industrial, new, d-and-c, warehouse); (commercial, refurb, architect-pm, work scope fire_services) — **the Benny example**; (residential, advisory, architect-pm, technical_dd scope). Legacy/no-taxonomy fixtures are optional compatibility checks only.
Assert per taxonomy fixture: skeleton headings exact; `pmp_min_words ≤ pmp_word_count(primary_view) ≤ pmp_max_words * 1.05`; the profile's top-weighted section is the longest non-snapshot section (fire upgrade → Compliance, and it names AS 2419.1/AS 2941 from loaded seed section refs; residential new → Scope, and it covers finishes/fixtures from seeds); no-document fixture has no `Grounded` claims and at least 4 open decision blocks; risk register ≤ 8 rows and contains derived flag rows; consultant roster includes work-scope consultants; no residential boilerplate ("BASIX", "HBCF") leaking into commercial drafts unless state-appropriate; `seed_consulted` includes required `path#section_id` refs.

## Definition of done

`uv run pytest tests/sitewise tests/workflows -v` green; a live smoke run of Create PMP on both a no-document `residential/new/house + budget $1M` project and a `commercial/refurb/office + fire_services` project produces scaffold-first drafts inside the 2–4 page primary band (manual review checkpoint for Benny), with required seed section refs recorded.
