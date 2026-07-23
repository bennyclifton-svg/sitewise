# PMP Brief / Consultants / Citations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make taxonomy-backed Create/Update PMP output read as a control document: Project Summary → Brief → Consultants → delivery sections → Citation key, with numbered `[n]` document citations and Brief/Consultants split.

**Architecture:** Update the taxonomy section contract (ids + labels + weights), then teach the platform-seeded scaffold renderer the new shape. Add a deterministic citation index over active project evidence documents and wire it into Summary, Consultants, and Citation key. Keep legacy 14-section `evidence_grounded` path unchanged except where shared helpers force minimal updates.

**Tech Stack:** Python 3.12, FastAPI sitewise modules, JSON taxonomy data, pytest.

**Design:** `docs/plans/2026-07-21-pmp-brief-consultants-citations-design.md`

---

### Task 1: Section contract — headings, ids, weights

**Files:**
- Modify: `backend/app/sitewise/section_contracts.py`
- Modify: `data/taxonomy/emphasis-profiles.json`
- Modify: `data/taxonomy/pmp-section-seed-map.json` (rename key only if id changes)
- Modify: `backend/tests/sitewise/test_section_contracts.py`
- Modify: `backend/tests/test_project_taxonomy_api.py`
- Modify: `backend/tests/sitewise/test_taxonomy.py` (if weight-key assertions need update)

**Decisions locked for this task:**
- Keep section **ids** stable where possible; only add new ids.
- Rename **labels** to design names.
- New ids: `consultants`, `citation-key`.
- Keep `scope-client-requirements` as id (label becomes **Brief**) so seed-map / weight keys stay stable.
- Final order:

| id | label |
| --- | --- |
| `snapshot` | Project Summary |
| `scope-client-requirements` | Brief |
| `consultants` | Consultants |
| `compliance-approvals` | Planning and Compliance |
| `programme` | Programme |
| `cost-budget` | Cost Planning |
| `procurement-delivery` | Procurement and Delivery |
| `risks` | Risks and mitigations |
| `actions-decisions` | Actions and decisions |
| `citation-key` | Citation key |

**Step 1: Write the failing test**

In `test_section_contracts.py`, replace the expected heading tuple to match the design labels and order (including Consultants and Citation key).

```python
def test_universal_skeleton_is_identical_across_classes() -> None:
    expected = (
        "Project Summary",
        "Brief",
        "Consultants",
        "Planning and Compliance",
        "Programme",
        "Cost Planning",
        "Procurement and Delivery",
        "Risks and mitigations",
        "Actions and decisions",
        "Citation key",
    )
    assert tuple(PMP_SECTION_HEADINGS.values()) == expected
    for building_class in building_classes():
        assert (
            required_section_headings(
                "architect-pm",
                building_class=building_class.value,
                work_type="new",
            )
            == expected
        )
```

Also update advisory variant assertions: Programme → still becomes "Programme of services"; Procurement and Delivery → "Services and deliverables". Citation key / Consultants have no advisory variants.

Update `test_project_taxonomy_api.py` expected `emphasis_profiles.sections` list to:

```python
[
    "snapshot",
    "scope-client-requirements",
    "consultants",
    "compliance-approvals",
    "programme",
    "cost-budget",
    "procurement-delivery",
    "risks",
    "actions-decisions",
    "citation-key",
]
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/sitewise/test_section_contracts.py tests/test_project_taxonomy_api.py::test_taxonomy_endpoint_returns_emphasis_profiles -v
```

Expected: FAIL on heading / sections list mismatch.

**Step 3: Minimal implementation**

1. Update `PMP_SECTION_HEADINGS` in `section_contracts.py` to the table above.
2. Update `data/taxonomy/emphasis-profiles.json`:
   - Insert `"consultants"` after `"scope-client-requirements"`.
   - Append `"citation-key"`.
   - For every `base_weights` profile: move ~half of current `scope-client-requirements` weight into `consultants` (consultant-roster weight leaves Brief). Give `citation-key` a small fixed weight (e.g. `0.04`) by trimming lightly from `actions-decisions` / surplus so weights still sum ≈ 1.0.
   - Leave modifiers targeting existing ids unchanged (no consultants/citation-key modifiers needed).
3. Leave `pmp-section-seed-map.json` keyed on `scope-client-requirements` (Brief seeds stay there). No consultants/citation-key seed routes required for v1.

**Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/sitewise/test_section_contracts.py tests/sitewise/test_taxonomy.py tests/test_project_taxonomy_api.py::test_taxonomy_endpoint_returns_emphasis_profiles -v
```

**Step 5: Commit**

```bash
git add backend/app/sitewise/section_contracts.py data/taxonomy/emphasis-profiles.json backend/tests/sitewise/test_section_contracts.py backend/tests/test_project_taxonomy_api.py
git commit -m "$(cat <<'EOF'
feat(pmp): add Consultants and Citation key to taxonomy section contract

Rename taxonomy PMP labels to the control-document structure and redistribute
Brief weight into Consultants while keeping seed-map ids stable.
EOF
)"
```

---

### Task 2: Citation index helper

**Files:**
- Create: `backend/app/sitewise/pmp_citations.py`
- Create: `backend/tests/sitewise/test_pmp_citations.py`

**Behavior:**
- Input: ordered list of active project evidence document descriptors `(path_or_label, date_or_status)`.
- Output: stable map `label → n` starting at 1, ordered by path/label ascending (deterministic).
- Format helpers: `citation_token(n) -> "[n]"`, `citation_or_dash(n | None) -> "[n]" | "—"`.
- Citation key line: `"[n] {filename} — {date/status}"`.
- Empty corpus → empty map; all citation cells use `—`.
- Do **not** invent citations for user-provided / assumption-only facts.

**Step 1: Write failing tests**

```python
from app.sitewise.pmp_citations import (
    CitationIndex,
    build_citation_index,
    format_citation_key_lines,
)


def test_build_citation_index_numbers_documents_in_stable_path_order() -> None:
    index = build_citation_index(
        [
            ("02-evidence/fee-proposal.pdf", "2026-03-01"),
            ("02-evidence/engagement-letter.pdf", "executed"),
            ("02-evidence/owner-brief.pdf", "draft"),
        ]
    )
    assert index.number_for("02-evidence/engagement-letter.pdf") == 1
    assert index.number_for("02-evidence/fee-proposal.pdf") == 2
    assert index.token_for("02-evidence/owner-brief.pdf") == "[3]"
    assert index.token_for("missing.pdf") == "—"


def test_citation_key_lines_are_short_and_numbered() -> None:
    index = build_citation_index(
        [("docs/b.pdf", "on file"), ("docs/a.pdf", "2026-01-01")]
    )
    assert format_citation_key_lines(index) == [
        "[1] a.pdf — 2026-01-01",
        "[2] b.pdf — on file",
    ]


def test_empty_corpus_has_no_numbers() -> None:
    index = build_citation_index([])
    assert index.documents == ()
    assert index.token_for("anything") == "—"
```

**Step 2: Run to verify fail**

```bash
cd backend && uv run pytest tests/sitewise/test_pmp_citations.py -v
```

**Step 3: Implement** `pmp_citations.py` with a small `CitationIndex` dataclass and the helpers above. Filename for key lines = basename of path.

**Step 4: Run to verify pass**

```bash
cd backend && uv run pytest tests/sitewise/test_pmp_citations.py -v
```

**Step 5: Commit**

```bash
git add backend/app/sitewise/pmp_citations.py backend/tests/sitewise/test_pmp_citations.py
git commit -m "$(cat <<'EOF'
feat(pmp): add deterministic document citation index

Assign one stable [n] per active evidence document for shared use across
Summary, Consultants, and Citation key.
EOF
)"
```

---

### Task 3: Renderer — Summary columns, Brief split, Consultants table, Citation key

**Files:**
- Modify: `backend/app/sitewise/pmp_renderer.py`
- Modify: `backend/tests/sitewise/test_greenfield_taxonomy.py`
- Modify: any other renderer tests that assert old headings/columns

**Target taxonomy scaffold behavior:**

1. **Project Summary** table columns: `| Field | Current PMP position | Citation |`
   - Middle cell: value + status label (e.g. `Walsh House renovation — User provided`).
   - Citation cell: `[n]` or `—` only (no document titles).
   - Remove the inline `_evidence_status_table()` from Summary (that content moves to Citation key).

2. **Brief** (`_render_taxonomy_scope`): physical/client brief only — inclusions, exclusions, interfaces, finishes/fixtures, acceptance criteria. **Remove** the `| Scope item | Expected consultants |` roster table and any "consultant information requests" framing that belongs in Consultants.

3. **Consultants** (new `_render_taxonomy_consultants`):

   `| Discipline | Firm | Scope / services | Fee | Status | Citation |`

   Rules:
   - First row: Architect-PM engagement when role applies (scope/fee/status from pack when available; else Assumption / TBC / `—`).
   - Then one row per taxonomy-expected discipline from `work_scope_items_for` (dedupe consultants). Missing appointment evidence → Assumption / Not evidenced with `—` citation.
   - When pack has engagement/fee facts, ground Architect-PM row and attach citation token from index if engagement/fee doc is in the index.

4. **Citation key** (new `_render_taxonomy_citation_key`, last section):
   1. Numbered document list (or a one-liner that no project evidence documents are cited yet).
   2. Section evidence-status table: `| Section | Evidence status | Citation |` for body sections (not Citation key itself).
   3. Short document-control note (draft/version, supersede rule).

5. Wire into `_render_taxonomy_platform_scaffold`:
   - Accept optional `citation_index: CitationIndex | None` and/or build from `pack.evidence_refs` when pack is passed.
   - For pure platform_seeded empty pack: empty index → all `—`.
   - Insert consultants after brief; citation key last.
   - Update programme column header `Evidence basis` → `Status` or keep status wording in middle columns; do not confuse with Citation key.

6. Update greenfield tests:
   - Heading names: "Planning and Compliance", "Brief", etc.
   - Weight assertions: `counts["Planning and Compliance"] > counts["Brief"]` (commercial fire); residential: `counts["Brief"] > counts["Planning and Compliance"]`.
   - Assert Consultants section exists and contains Fire Engineer (or roster disciplines).
   - Assert Brief does **not** contain `| Expected consultants |`.
   - Assert Summary header is `| Field | Current PMP position | Citation |`.
   - Assert last `##` heading is `Citation key`.

**Step 1: Write/update failing tests in `test_greenfield_taxonomy.py`** reflecting the behaviors above.

**Step 2: Run**

```bash
cd backend && uv run pytest tests/sitewise/test_greenfield_taxonomy.py -v
```

Expected: FAIL on headings/columns/roster location.

**Step 3: Implement renderer changes** (minimal; reuse `work_scope_items_for` for roster disciplines).

For scaffold entry without a full evidence pack of paths, build index from `pack.evidence_refs` sorted. Platform_seeded create often has empty refs — that is fine.

Pass `version` into Citation key document-control note.

**Step 4: Re-run greenfield + section contract tests**

```bash
cd backend && uv run pytest tests/sitewise/test_greenfield_taxonomy.py tests/sitewise/test_section_contracts.py -v
```

**Step 5: Commit**

```bash
git add backend/app/sitewise/pmp_renderer.py backend/tests/sitewise/test_greenfield_taxonomy.py
git commit -m "$(cat <<'EOF'
feat(pmp): render Brief/Consultants split and Citation key

Move consultant roster out of Brief, add appointment register, and close
taxonomy PMPs with a numbered Citation key instead of front-loaded evidence.
EOF
)"
```

---

### Task 4: Greenfield brief, length, and adaptive contract copy

**Files:**
- Modify: `backend/app/sitewise/pmp_greenfield_brief.py`
- Modify: `backend/app/sitewise/pmp_length.py` (if snapshot exclusion list needs `citation-key` treated like snapshot — citation-key should stay short; exclude from "top weighted" candidates like snapshot)
- Modify: tests asserting "Compliance and approvals" / "Scope and client requirements" in brief text

**Step 1: Failing tests**

Update `test_adaptive_greenfield_contract_has_budgets_and_fire_as_refs`:
- Expect `"Planning and Compliance (~"` not `"Compliance and approvals (~"`.
- Expect consultants listed under Consultants focus line, not only under Brief.
- Brief focus line must mention physical brief / finishes, not expected-consultant roster as primary content.

**Step 2: Run → fail**

**Step 3: Implement**
- `_contract_focus_line`: rename `scope-client-requirements` focus to Brief (physical only); add `consultants` focus (appointment register, Architect-PM first, taxonomy disciplines); add short `citation-key` focus (numbered docs + section status table + document control).
- Move the work-scope consultant listing currently under Brief into the Consultants section block of `_adaptive_greenfield_brief`.
- `_top_weighted_section_id` / `pmp_length` candidates: exclude both `snapshot` and `citation-key`.

**Step 4: Pass tests + commit**

```bash
git commit -m "$(cat <<'EOF'
feat(pmp): align greenfield contract with Brief and Consultants

Point adaptive word budgets and focus lines at the new section labels and
keep Citation key out of emphasis competition.
EOF
)"
```

---

### Task 5: Create/Update PMP instructions and prompt fixtures

**Files:**
- Modify: `backend/app/workflows/create_pmp_instructions.md`
- Modify: `backend/tests/workflows/test_create_pmp.py` (and any fixtures using old headings)
- Modify: `backend/tests/workflows/test_pmp_minimal_brief_lifecycle.py` if it asserts Evidence basis / old taxonomy headings for taxonomy path
- Modify: `backend/tests/sitewise/test_pmp_length.py`, `test_pmp_coverage.py` fixtures that hardcode old headings

**Taxonomy / adaptive instructions (primary):**
- Use exact universal headings from the prompt (new names).
- Project Summary: `Field | Current PMP position | Citation` with `[n]` or `—`.
- Brief = physical/client only; Consultants = appointment register.
- Shared `[n]` numbering; Citation key only at end; do not open with Evidence basis.
- platform_seeded: still no **Grounded**.

**Evidence-grounded legacy rules:** keep the existing Evidence basis rules for the legacy 14-section path (out of scope to redesign), but add a short note that when the Adaptive taxonomy contract is present, Citation key + `[n]` rules supersede front-loaded Evidence basis.

**Step 1: Update tests that sniff instruction / prompt text for old headings.**

**Step 2: Fail → update markdown + fixture strings → pass.**

**Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
docs(pmp): instruct models on Brief/Consultants and numbered citations

Update Create/Update PMP agent instructions and workflow fixtures for the
taxonomy control-document structure.
EOF
)"
```

---

### Task 6: Evidence validation / sanitize heading lists (taxonomy-safe)

**Files:**
- Modify: `backend/app/sitewise/pmp_evidence_validation.py`
- Modify: `backend/tests/sitewise/test_pmp_evidence_validation.py`
- Possibly: `pmp_decisions.py` section string `"Project snapshot"` → `"Project Summary"` if taxonomy decisions use it

**Scope:**
- Do **not** rewrite legacy Evidence basis validators for the 14-section path.
- Update any shared heading lists used when taxonomy PMPs are sanitized/downgraded so they recognize **Brief**, **Project Summary**, **Consultants**, **Citation key** instead of only old labels.
- If `apply_corpus_evidence_downgrades` hardcodes `"Scope and client requirements"`, add/replace with `"Brief"`.
- `taxonomy_provenance_violations` remains: no Grounded in platform_seeded.

**Step 1: Add/adjust a focused test** that a taxonomy markdown with Citation key (and no front Evidence basis) does not fail taxonomy provenance checks solely for missing Evidence basis.

**Step 2–4: TDD implement, pass, commit.**

```bash
git commit -m "$(cat <<'EOF'
fix(pmp): recognize new taxonomy headings in evidence helpers

Keep legacy Evidence basis validation for non-taxonomy drafts while teaching
sanitize/downgrade lists the Brief/Citation key labels.
EOF
)"
```

---

### Task 7: Sweep remaining test fixtures and full suite gate

**Files:** any remaining under `backend/tests/sitewise/` and `backend/tests/workflows/` that still assert:
- `Project snapshot`
- `Scope and client requirements`
- `Compliance and approvals`
- `Programme and milestones`
- `Cost and budget`
- Expected consultants column inside Brief
- Evidence basis as first taxonomy section

**Step 1:** Grep and update fixtures/assertions.

```bash
cd backend && rg -n "Project snapshot|Scope and client requirements|Compliance and approvals|Programme and milestones|Cost and budget|Expected consultants|Evidence basis and document control" tests/
```

**Step 2:** Run focused then broad suites:

```bash
cd backend && uv run pytest tests/sitewise/ tests/workflows/test_create_pmp.py tests/workflows/test_update_pmp.py tests/workflows/test_pmp_minimal_brief_lifecycle.py tests/test_project_taxonomy_api.py -q
```

Fix failures without expanding scope into legacy 14-section redesign.

**Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
test(pmp): align fixtures with Brief/Consultants citation structure

Update remaining SiteWise and workflow expectations for the redesigned
taxonomy PMP section set.
EOF
)"
```

---

## Out of scope (do not implement)

- Legacy non-taxonomy role section contracts (14-section architect-pm evidence_grounded scaffold)
- Claim/passage-level citation numbering
- Companion annexure redesign beyond what primary PMP needs for the split

## Done when

- Taxonomy `platform_seeded` scaffold headings match the design order and labels
- Brief has no Expected consultants roster; Consultants has the appointment register
- Summary uses Citation column with `[n]` / `—`
- Citation key is the last section with numbered docs + section status table + document-control note
- Weights include consultants; Brief weight reduced accordingly
- Instructions and tests updated; targeted pytest suites green
