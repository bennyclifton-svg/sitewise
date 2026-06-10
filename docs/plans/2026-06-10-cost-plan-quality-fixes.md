# Cost Plan Quality Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> **DO NOT DELETE THIS PLAN** with the older `docs/plans/2026-06-*` structural plans. This one was written 2026-06-10 to fix the Chen Residence cost plan v8 critique.

**Goal:** Fix six quality defects in the hybrid Create Cost Plan compiler so the generated cost plan is internally coherent, fully evidence-grounded, honestly labelled, and meets the doctrine's "most complete useful view" mandate — one defect at a time, minimal change each.

**Architecture:** The cost plan that was critiqued is produced by the **hybrid compiler** path (`run_create_cost_plan_hybrid` in [create_cost_plan.py:618](../../backend/app/workflows/create_cost_plan.py#L618)), which runs `extract → render → narrate → assemble`. The deterministic scaffold (tables, totals, audit Facts/Assumptions, gaps, evidence map) is built in [cost_plan_renderer.py](../../backend/app/sitewise/cost_plan_renderer.py) from a `CostPlanEvidencePack` extracted in [cost_plan_evidence.py](../../backend/app/sitewise/cost_plan_evidence.py) / [mobilisation_evidence.py](../../backend/app/sitewise/mobilisation_evidence.py). Only risks/judgements/recommendations/next-steps come from the LLM ([cost_plan_narrative.py](../../backend/app/workflows/cost_plan_narrative.py)) and are merged by [cost_plan_assembler.py](../../backend/app/sitewise/cost_plan_assembler.py). **Five of six fixes live in the renderer or evidence extractor; one lives in the narrative validator + instructions.** The legacy LLM-only path ([create_cost_plan_instructions.md](../../backend/app/workflows/create_cost_plan_instructions.md)) is NOT the generator for architect-pm projects and is out of scope.

**Tech Stack:** Python 3.12, pydantic, pydantic-ai, pytest. Run tests with `uv run pytest` from `backend/`.

**Scope discipline:** Each task is one defect. Do not start the next task until the current task's tests pass and it is committed. The tasks are ordered so they compose without rework (Task 1's grand-total helper is designed so Task 6's benchmark rows fold in cleanly).

**Task order (by interaction risk, lowest first):**
1. Grand-total incoherence (renderer)
2. False "no gaps" / "no assumptions" (renderer)
3. Owner-supplied GST basis asserted/inverted (renderer)
4. Certifier grounding miss (evidence extractor + renderer)
5. Generic risk owners "Project Team" (narrative validator + instructions)
6. Benchmark construction split — "most complete useful view" (renderer)

---

## Task 1: Grand total must equal the sum of its own visible subtotals

**Problem:** The cost-breakdown table's **Grand total (ex GST)** is set to `_known_indicative_total_ex_gst(pack)` (= construction ceiling + contingency + fee + owner-supplied = $2,148,500), but the Construction/Consultants/PC subtotals show `TBC` and the $1.85M ceiling appears as no line in the table. So the grand total ≠ the sum of the visible subtotal rows ($148,500 + $120,000 = $268,500). This is hardcoded false precision and would force a broken Excel total. The whole-project indicative envelope is correct where it already lives — in `_render_total_budget` ("Total approved or indicative budget") — it must NOT be reused as the breakdown-table total.

**Fix:** Compute the breakdown-table grand total as the sum of the *numeric* subtotal rows actually present in the table. Leave `_render_total_budget` and `_known_indicative_total_ex_gst` untouched.

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py` — `_render_cost_breakdown` (lines ~420–431)
- Test: `backend/tests/sitewise/test_cost_plan_renderer.py`

**Step 1: Write the failing test**

Add to `backend/tests/sitewise/test_cost_plan_renderer.py`:

```python
def _breakdown_section(markdown: str) -> str:
    out, collecting = [], False
    for line in markdown.splitlines():
        s = line.strip().lower()
        if s.startswith("## ") and s[3:].strip() == "cost breakdown by category":
            collecting = True
            continue
        if collecting and s.startswith("## "):
            break
        if collecting:
            out.append(line)
    return "\n".join(out)


def _money_to_int(cell: str) -> int | None:
    cell = cell.replace("$", "").replace(",", "").strip()
    return int(cell) if cell.isdigit() else None


def test_grand_total_equals_sum_of_visible_subtotals() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    section = _breakdown_section(markdown)
    subtotals, grand = [], None
    for line in section.splitlines():
        if "subtotal —" in line.lower():
            cell = line.split("|")[4]
            amount = _money_to_int(cell)
            if amount is not None:
                subtotals.append(amount)
        if "grand total (ex gst)" in line.lower():
            grand = _money_to_int(line.split("|")[4])
    assert grand is not None
    assert grand == sum(subtotals), f"grand {grand} != sum(subtotals) {sum(subtotals)}"
    # The whole-project envelope ($2,148,500) must NOT be the breakdown grand total.
    assert grand != 2_148_500
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py::test_grand_total_equals_sum_of_visible_subtotals -v`
Expected: FAIL — grand total is 2,148,500, sum of visible subtotals is 268,500.

**Step 3: Write minimal implementation**

In `cost_plan_renderer.py` `_render_cost_breakdown`, replace the grand-total block (currently using `_known_indicative_total_ex_gst`):

```python
    subtotal_amounts = [
        _parse_amount(fee_subtotal),
        _parse_amount(contingency),
    ]
    itemised_total = sum(amount for amount in subtotal_amounts if amount is not None)
    grand_total = f"${itemised_total:,}" if itemised_total else "TBC"
    grand_basis = "Sum of itemised subtotals — excludes construction ceiling and TBC lines"
    rows.extend(
        [
            f"| | | **Subtotal — Fees and charges** | {fee_subtotal} | | |",
            "| | | **Subtotal — Consultants** | TBC | | |",
            "| | | **Subtotal — Construction** | TBC | | |",
            "| | | **Subtotal — PC allowances** | TBC | | |",
            f"| | | **Subtotal — Contingency / allowances** | {contingency} | | |",
            f"| | | **Grand total (ex GST)** | {grand_total} | Assumption | {grand_basis} |",
        ]
    )
```

Leave `_known_indicative_total_ex_gst` and its use in `_render_total_budget` as-is. (`_parse_amount` already handles `"$148,500"`.)

**Step 4: Run the full renderer suite to verify pass + no regressions**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py -v`
Expected: PASS, including the existing `test_render_cost_plan_scaffold_*` tests (none assert the old $2,148,500 in the breakdown table — verify).

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "fix(cost-plan): make breakdown grand total equal sum of visible subtotals"
```

---

## Task 2: Stop claiming "no gaps" / "no assumptions" when the breakdown is full of assumptions

**Problem:** For Chen, `pack.gaps` is empty (brief, budget, geotech, certifier, programme all present), so:
- `_render_source_evidence` prints `**Gaps:** None identified beyond construction tender pricing.`
- `_render_internal_audit` prints `Assumption: none identified.`

…even though the breakdown carries ~20 rows explicitly labelled **Assumption**. The audit layer (the credibility backstop) contradicts the document.

**Fix:** The cost plan always carries standing structural assumptions in mobilisation-stage evidence_grounded mode (construction unpriced, consultants not appointed, authority fees not benchmarked, PC pending). Emit those always; never say "none identified."

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py` — `_render_source_evidence` (gaps line ~253–254) and `_render_internal_audit` (assumptions fallback ~642)
- Test: `backend/tests/sitewise/test_cost_plan_renderer.py`

**Step 1: Write the failing test**

```python
def test_audit_assumptions_never_claims_none_when_breakdown_has_assumptions() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "assumption: none identified" not in markdown
    assert "none identified beyond construction tender pricing" not in markdown
    # standing assumptions must be present
    assert "construction trade pricing" in markdown
    assert "consultant fees" in markdown
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py::test_audit_assumptions_never_claims_none_when_breakdown_has_assumptions -v`
Expected: FAIL on the `"assumption: none identified"` assertion.

**Step 3: Write minimal implementation**

Add a module-level constant near the other row tuples in `cost_plan_renderer.py`:

```python
_STANDING_ASSUMPTIONS: tuple[str, ...] = (
    "Construction trade pricing TBC pending head-builder tender.",
    "Consultant fees (structural, geotechnical, survey, hydraulic, energy) TBC — not yet appointed.",
    "Authority and statutory fees (DA/CC, BASIX, Sydney Water, levies) TBC — benchmark only.",
    "PC allowance lines are placeholders until contract Schedule of Allowances.",
)
```

In `_render_source_evidence`, replace the gaps line:

```python
            "**Gaps:** "
            + (
                "; ".join(pack.gaps)
                if pack.gaps
                else "No mobilisation evidence gaps; construction trade pricing, consultant "
                "fees and authority charges remain unpriced (see Assumptions and exclusions)."
            ),
```

In `_render_internal_audit`, replace:

```python
    assumptions = [f"Assumption: {gap}." for gap in pack.gaps] or ["Assumption: none identified."]
```

with:

```python
    assumptions = [f"Assumption: {gap}." for gap in pack.gaps]
    assumptions.extend(f"Assumption: {item}" for item in _STANDING_ASSUMPTIONS)
```

**Step 4: Run the suite**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py -v`
Expected: PASS. (Check `_render_assumptions_exclusions` still reads well — it already lists similar items; minor duplication between the Assumptions section and the audit layer is acceptable and intentional.)

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "fix(cost-plan): never report 'no gaps/no assumptions' when breakdown carries assumptions"
```

---

## Task 3: Do not assert owner-supplied items are ex-GST (and stop fabricating an inc-GST gross-up)

**Problem:** The owner brief states allowances ("pendant lights $8,000", "appliances $22,000") with **no GST basis**. The renderer stores them as `amount_ex_gst`, asserts "ex GST", and grosses them up to "$33,000 inc GST reference". Consumer retail allowances are almost certainly inc-GST already, so the gross-up is likely inverted — an assumption presented as fact.

**Fix (minimal, presentation-only):** Stop asserting ex/inc and stop deriving an inc-GST figure for owner-supplied items. Present the brief figure as stated and label the basis as not stated. Do not rename the `amount_ex_gst` field (invasive); only change rendered text.

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py` — `_owner_supplied_lines` (~156–166), `_render_total_budget` owner-supplied bullet (~329–335), `_render_gst_basis` owner-supplied translation (~366–368), `_render_internal_audit` owner-supplied fact (~627–630), and `_render_allowances_contingency` per-item lines (~487–491)
- Test: `backend/tests/sitewise/test_cost_plan_renderer.py` (update existing assertion at line 53)

**Step 1: Update the existing test + add a guard test**

In `test_render_cost_plan_scaffold_surfaces_owner_brief_ceiling`, change line 53 from:

```python
    assert "pendant lights: $8,000 ex gst (owner-supplied)" in markdown
```

to:

```python
    assert "pendant lights: $8,000 (owner-supplied" in markdown
```

Add:

```python
def test_owner_supplied_items_do_not_assert_gst_basis() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "$33,000 inc gst" not in markdown
    assert "owner-supplied allowances inc gst" not in markdown
    assert "gst basis not stated" in markdown
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py::test_owner_supplied_items_do_not_assert_gst_basis -v`
Expected: FAIL — "$33,000 inc gst" present, "gst basis not stated" absent.

**Step 3: Minimal implementation**

`_owner_supplied_lines`:

```python
def _owner_supplied_lines(items: list[OwnerSuppliedItem]) -> list[str]:
    if not items:
        return ["- Owner-supplied items: **Assumption — not yet listed in evidence**."]
    lines: list[str] = ["- **Owner-supplied items (below contract sum):**"]
    for item in items:
        amount = _money(item.amount_ex_gst) if item.amount_ex_gst else "TBC"
        lines.append(f"  - {item.label}: {amount} (owner-supplied; GST basis not stated in brief)")
    total = _owner_supplied_total_ex_gst(items)
    if total:
        lines.append(
            f"  - **Owner-supplied subtotal:** ${total:,} (owner brief allowance; GST basis not stated)."
        )
    return lines
```

`_render_total_budget` owner-supplied bullet:

```python
            lines.append(
                f"- **Owner-supplied allowances (additional):** ${total:,} — owner procurement "
                "outside builder contract (owner brief allowance; GST basis not stated)."
            )
```

`_render_gst_basis`: remove the owner-supplied translation (delete the `owner_supplied_total` block that appends `Owner-supplied allowances inc GST: ...`).

`_render_allowances_contingency` per-item line:

```python
            lines.append(f"  - {item.label}: {amount} (owner-supplied; GST basis not stated)")
```

`_render_internal_audit` owner-supplied fact:

```python
            facts.append(f"Owner-supplied allowances total ${total:,} per owner brief (GST basis not stated).")
```

> Note: the `_inc_gst` helper stays — it is still used for fee/ceiling/contingency translations. Whether contingency should be grossed up by GST at all is a separate, smaller question; leave it for a follow-up, do not expand this task.

**Step 4: Run the suite**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py -v`
Expected: PASS, including the edited `test_render_cost_plan_scaffold_surfaces_owner_brief_ceiling`.

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "fix(cost-plan): stop asserting/inverting GST basis on owner-supplied items"
```

---

## Task 4: Ground the principal certifier — it is appointed with an evidenced fee

**Problem:** Cost code 11 "Principal certifier" always renders `TBC | Assumption | Not yet appointed`, contradicting (a) evidence file 12 (Certify NSW appointed, fee **$6,800 + GST**, effective 1 June 2026) and (b) the plan's own gate row "Grounded — principal certifier appointed." The evidenced fee is dropped.

**Fix:** Extract certifier name + fee in the evidence pack, then render the certifier consultant row as grounded with the fee, and add the certifier to the locked-appointments table — only when `GAP_CERTIFIER` is absent.

**Files:**
- Modify: `backend/app/sitewise/cost_plan_evidence.py` — add `certifier_name` / `certifier_fee_ex_gst` to `CostPlanEvidencePack`; extract from combined source text
- Modify: `backend/app/sitewise/cost_plan_renderer.py` — `_render_cost_breakdown` certifier consultant row; `_render_locked_appointments`
- Test: `backend/tests/sitewise/test_cost_plan_evidence.py` and `test_cost_plan_renderer.py`

**Step 1: Write failing tests**

In `test_cost_plan_evidence.py` (uses the same fixtures):

```python
def test_extract_certifier_appointment_and_fee() -> None:
    pack = _pack()  # reuse the module's pack helper / build from fixtures incl. 12-certifier
    assert pack.certifier_fee_ex_gst == "$6,800"
    assert pack.certifier_name and "certify nsw" in pack.certifier_name.lower()
```

In `test_cost_plan_renderer.py`:

```python
def test_certifier_row_is_grounded_when_appointed() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    # consultant row 11 must not say "not yet appointed" for the certifier
    assert "principal certifier | tbc | assumption | not yet appointed" not in markdown
    assert "$6,800" in markdown
    assert "certify nsw" in markdown
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_evidence.py::test_extract_certifier_appointment_and_fee tests/sitewise/test_cost_plan_renderer.py::test_certifier_row_is_grounded_when_appointed -v`
Expected: FAIL — fields missing / "$6,800" absent.

**Step 3: Minimal implementation**

In `cost_plan_evidence.py`, add patterns + fields. File 12 contains lines like `Fee: Owner direct — $6,800 + GST` and `appointed Certify NSW Pty Ltd`:

```python
_CERTIFIER_NAME_PATTERN = re.compile(
    r"appointed\s+([A-Z][\w&.'\- ]+?Pty Ltd)\s+as principal certifier",
    re.IGNORECASE,
)
_CERTIFIER_FEE_PATTERN = re.compile(
    r"(?:principal certifier|certifier|PCA)[^.\n]*?\$\s*([\d,]+)\s*\+?\s*GST",
    re.IGNORECASE,
)
```

Add fields to `CostPlanEvidencePack`:

```python
    certifier_name: str | None = None
    certifier_fee_ex_gst: str | None = None
```

In `extract_cost_plan_evidence_pack`, after building `mobilisation`, scan combined text (only trust it when the certifier gap is closed):

```python
    combined = "\n\n".join(source_texts)
    certifier_name = None
    certifier_fee = None
    if not pack_has_gap(mobilisation, GAP_CERTIFIER):
        name_match = _CERTIFIER_NAME_PATTERN.search(combined)
        fee_match = _CERTIFIER_FEE_PATTERN.search(combined)
        certifier_name = name_match.group(1).strip() if name_match else None
        certifier_fee = f"${fee_match.group(1)}" if fee_match else None
```

(Import `pack_has_gap` and `GAP_CERTIFIER` from `mobilisation_evidence` — `extract_mobilisation_evidence_pack` is already imported there.) Pass both into the `CostPlanEvidencePack(...)` constructor.

In `cost_plan_renderer.py` `_render_cost_breakdown`, special-case the certifier consultant row inside the `_CONSULTANT_ROWS` loop:

```python
    for code, label in _CONSULTANT_ROWS:
        if label == "Principal certifier" and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
            fee = _money(pack.certifier_fee_ex_gst) if pack.certifier_fee_ex_gst else "Owner-direct"
            name = pack.certifier_name or "appointed"
            rows.append(
                f"| {code} | Consultants | {label} | {fee} | Grounded | "
                f"Appointed ({name}); owner-direct fee |"
            )
            continue
        rows.append(
            f"| {code} | Consultants | {label} | TBC | Assumption | Not yet appointed |"
        )
```

In `_render_locked_appointments`, append a certifier row when appointed:

```python
    rows = [
        "## Known locked contract and appointment values",
        "",
        "| Supplier | Scope | Amount (ex GST) | Date | Evidence |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {mob.appointee or 'Harrison Clarke Studio Pty Ltd'} | Architect / PM | "
            f"{fee} | {executed} | Engagement letter |"
        ),
    ]
    if pack.certifier_name and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
        cert_fee = _money(pack.certifier_fee_ex_gst) if pack.certifier_fee_ex_gst else "Owner-direct"
        rows.append(
            f"| {pack.certifier_name} | Principal certifier | {cert_fee} | Appointed | "
            "Certifier appointment |"
        )
    rows.extend(
        [
            "",
            "All other consultant and construction appointments: **Assumption — not yet locked**.",
        ]
    )
    return "\n".join(rows)
```

(`GAP_CERTIFIER` and `pack_has_gap` are already imported in the renderer.)

**Step 4: Run the suites**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_evidence.py tests/sitewise/test_cost_plan_renderer.py -v`
Expected: PASS. If the consultant subtotal logic in Task 6 later sums consultant rows, the $6,800 will fold in there — fine.

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_evidence.py backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_evidence.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "fix(cost-plan): ground appointed principal certifier with evidenced fee"
```

---

## Task 5: Reject generic risk owners ("Project Team")

**Problem:** Every risk row in v8 has Owner = "Project Team". The renderer skeleton ([cost_plan_renderer.py:59-95](../../backend/app/sitewise/cost_plan_renderer.py#L59-L95)) has specific owners, but the narrative LLM replaces all risk rows and the assembler uses them verbatim ([cost_plan_assembler.py:46-52](../../backend/app/sitewise/cost_plan_assembler.py#L46-L52)). Nothing constrains `RiskRow.owner`.

**Fix:** Add a validator rule to `validate_cost_plan_narrative_output` that flags generic owners, feeding the existing 3-attempt retry loop; reinforce with an instruction line. This matches every other narrative rule in that file.

**Files:**
- Modify: `backend/app/workflows/cost_plan_narrative.py` — `validate_cost_plan_narrative_output`
- Modify: `backend/app/workflows/cost_plan_narrative_instructions.md`
- Test: `backend/tests/workflows/test_cost_plan_narrative.py`

**Step 1: Write the failing test**

In `test_cost_plan_narrative.py` (build a minimal valid `CostPlanNarrativeOutput` with all risk owners = "Project Team", then call the validator and expect it to raise). Follow the existing test patterns in that file for constructing `pack` and `output`:

```python
import pytest
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.cost_plan_narrative import validate_cost_plan_narrative_output, CostPlanNarrativeOutput
from app.workflows.pmp_narrative import RiskRow


def test_validator_rejects_generic_risk_owner(_chen_pack, _run_date):  # reuse existing fixtures/helpers
    rows = [
        RiskRow(risk=f"Risk {i}", owner="Project Team", status="Open",
                next_action="Do thing 2026-07-01", due_date="2026-07-01")
        for i in range(5)
    ]
    output = CostPlanNarrativeOutput(
        judgements=["j1", "j2"],
        recommendations=["r1 2026-07-01", "r2 2026-07-02", "r3 2026-07-03"],
        risk_rows=rows,
        next_steps=["s1 2026-07-01", "s2 2026-07-02", "s3 2026-07-03"],
    )
    with pytest.raises(WorkflowValidationError, match="generic"):
        validate_cost_plan_narrative_output(output, _chen_pack, run_date=_run_date)
```

(If the test module has no shared pack/run_date fixtures, construct the pack via `extract_cost_plan_evidence_pack` on the fixtures and use `date(2026, 6, 10)`, mirroring the existing tests in the file.)

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/workflows/test_cost_plan_narrative.py::test_validator_rejects_generic_risk_owner -v`
Expected: FAIL — no error raised (validator currently ignores owner).

**Step 3: Minimal implementation**

In `validate_cost_plan_narrative_output`, add near the other risk checks:

```python
    _GENERIC_OWNERS = {"project team", "team", "project", "tbc", "n/a", "various", "all"}
    for index, row in enumerate(output.risk_rows, start=1):
        if row.owner.strip().lower() in _GENERIC_OWNERS:
            issues.append(
                f"risk row {index} owner {row.owner!r} is generic — assign a specific "
                "accountable party (Owner, Architect-PM, Structural Engineer, Certifier, Builder)"
            )
```

(Define `_GENERIC_OWNERS` at module level rather than inside the function if you prefer; either is fine.)

In `cost_plan_narrative_instructions.md`, add under the risk-row rules:

```markdown
12. Each `risk_rows` owner MUST be a specific accountable party — `Owner`, `Architect-PM`,
    `Structural Engineer`, `Certifier`, or `Builder`. Never use generic owners such as
    "Project Team", "Team", "Project", or "Various".
```

**Step 4: Run the suite**

Run: `cd backend && uv run pytest tests/workflows/test_cost_plan_narrative.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/workflows/cost_plan_narrative.py backend/app/workflows/cost_plan_narrative_instructions.md backend/tests/workflows/test_cost_plan_narrative.py
git commit -m "fix(cost-plan): reject generic risk owners in narrative validation"
```

---

## Task 6: Deliver a benchmark construction split (the "most complete useful view" mandate)

**Problem:** Doctrine ([cost-plan-system.md:5,60](../../data/skills/systems/cost-plan-system.md#L60)) requires the cost plan to be "the most complete useful whole-project cost view the evidence supports" and to "draft a benchmark framework, clearly labelled as Judgement or Assumption" when no tender exists. The renderer leaves every construction row at bare `TBC`. With an evidenced **$1,850,000 construction ceiling**, the plan should distribute an indicative elemental split across the 9 construction rows, labelled Benchmark/Assumption, summing to the ceiling — turning the empty grid into a usable framework and making the Construction subtotal meaningful.

**Reference:** taxonomy from [nsw-residential-cost-breakdown-reference.md](../../data/skills/reference/nsw-residential-cost-breakdown-reference.md) (families only — it deliberately carries no rates). The percentage split below is a practice-benchmark Assumption, not market-rate advice.

**Fix:** When `pack.construction_budget_ceiling` is present, render each construction row's Budget as a benchmark % of the ceiling (Status `Assumption`, Basis `Benchmark % of ceiling`), set the Construction subtotal to the ceiling, and fold the Construction subtotal into the grand-total sum from Task 1. When the ceiling is absent, keep the current `TBC` behaviour.

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py` — add benchmark split constant; `_render_cost_breakdown` construction rows, Construction subtotal, and grand-total sum list
- Test: `backend/tests/sitewise/test_cost_plan_renderer.py`

**Step 1: Write the failing test**

```python
def test_construction_rows_benchmarked_to_ceiling() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    section = _breakdown_section(markdown)  # helper from Task 1
    construction_amounts = []
    construction_subtotal = None
    for line in section.splitlines():
        low = line.lower()
        if "| construction |" in low and "subtotal" not in low:
            amount = _money_to_int(line.split("|")[4])
            if amount is not None:
                construction_amounts.append(amount)
        if "subtotal — construction" in low:
            construction_subtotal = _money_to_int(line.split("|")[4])
    assert len(construction_amounts) == 9
    assert construction_subtotal == 1_850_000
    assert sum(construction_amounts) == 1_850_000
    assert "benchmark % of ceiling" in markdown.lower()
```

Also assert the grand total now reconciles with the benchmarked construction subtotal:

```python
def test_grand_total_includes_benchmarked_construction() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    section = _breakdown_section(markdown)
    subtotals, grand = [], None
    for line in section.splitlines():
        if "subtotal —" in line.lower():
            amount = _money_to_int(line.split("|")[4])
            if amount is not None:
                subtotals.append(amount)
        if "grand total (ex gst)" in line.lower():
            grand = _money_to_int(line.split("|")[4])
    assert grand == sum(subtotals)
    assert grand >= 1_850_000 + 148_500 + 120_000
```

**Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py::test_construction_rows_benchmarked_to_ceiling tests/sitewise/test_cost_plan_renderer.py::test_grand_total_includes_benchmarked_construction -v`
Expected: FAIL — construction rows are TBC, subtotal is TBC.

**Step 3: Minimal implementation**

Add a benchmark split constant aligned to `_CONSTRUCTION_ROWS` (sums to 100):

```python
# Practice-benchmark elemental split (Assumption — not market-rate advice).
# Keys MUST match _CONSTRUCTION_ROWS labels in order; integer percents sum to 100.
_CONSTRUCTION_BENCHMARK_PCT: tuple[tuple[str, int], ...] = (
    ("Preliminaries", 8),
    ("Siteworks and demolition", 7),
    ("Footings and slab", 12),
    ("Framing and roof", 18),
    ("External envelope and lockup", 15),
    ("Internal linings and joinery", 14),
    ("Kitchen and bathrooms", 9),
    ("Building services", 10),
    ("Finishes and external works", 7),
)
```

In `_render_cost_breakdown`, compute the ceiling and replace the construction loop. Distribute by percentage and put any rounding remainder on the last row so rows sum exactly to the ceiling:

```python
    ceiling = _parse_amount(pack.construction_budget_ceiling)
    if ceiling is not None:
        running = 0
        last_index = len(_CONSTRUCTION_BENCHMARK_PCT) - 1
        pct_by_label = dict(_CONSTRUCTION_BENCHMARK_PCT)
        for index, (code, label) in enumerate(_CONSTRUCTION_ROWS):
            if index == last_index:
                amount = ceiling - running
            else:
                amount = round(ceiling * pct_by_label[label] / 100)
                running += amount
            rows.append(
                f"| {code} | Construction | {label} | ${amount:,} | Assumption | "
                f"Benchmark % of ceiling |"
            )
        construction_subtotal = f"${ceiling:,}"
    else:
        for code, label in _CONSTRUCTION_ROWS:
            rows.append(
                f"| {code} | Construction | {label} | TBC | Assumption | Pending head-builder tender |"
            )
        construction_subtotal = "TBC"
```

Update the subtotal/grand-total block to use `construction_subtotal` and add it to the sum list from Task 1:

```python
    subtotal_amounts = [
        _parse_amount(fee_subtotal),
        _parse_amount(construction_subtotal),
        _parse_amount(contingency),
    ]
    itemised_total = sum(amount for amount in subtotal_amounts if amount is not None)
    grand_total = f"${itemised_total:,}" if itemised_total else "TBC"
    grand_basis = "Sum of itemised subtotals — construction is benchmark % of ceiling, consultants/PC TBC"
    rows.extend(
        [
            f"| | | **Subtotal — Fees and charges** | {fee_subtotal} | | |",
            "| | | **Subtotal — Consultants** | TBC | | |",
            f"| | | **Subtotal — Construction** | {construction_subtotal} | | |",
            "| | | **Subtotal — PC allowances** | TBC | | |",
            f"| | | **Subtotal — Contingency / allowances** | {contingency} | | |",
            f"| | | **Grand total (ex GST)** | {grand_total} | Assumption | {grand_basis} |",
        ]
    )
```

Add a one-line note above the table clarifying the benchmark basis (so a reader knows the construction rows are an indicative split, not priced):

```python
            "Construction rows are an indicative benchmark split of the owner ceiling "
            "(Assumption) until head-builder tender returns a priced schedule.",
```

**Step 4: Run the full cost-plan suite**

Run: `cd backend && uv run pytest tests/sitewise/test_cost_plan_renderer.py tests/sitewise/test_cost_plan_evidence.py tests/workflows/test_cost_plan_narrative.py tests/workflows/test_create_cost_plan.py tests/workflows/test_create_cost_plan_hybrid_integration.py -v`
Expected: PASS. Watch the hybrid integration test and `cost_plan_evidence_grounded_violations` (claim-first construction-line-count check) — more construction rows only helps it.

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "feat(cost-plan): benchmark construction split from owner ceiling"
```

---

## Final verification (after all six tasks)

Run the whole cost-plan surface and confirm green before declaring done:

```bash
cd backend && uv run pytest tests/sitewise/ tests/workflows/ -k "cost_plan or create_cost_plan" -v
```

Then regenerate the Chen Residence cost plan (or re-run the hybrid integration fixture) and re-read the six critique points to confirm each is resolved in the actual output, not just in unit tests.

## Deferred / out of scope (note, do not silently expand tasks)

- Authority/consultant **fee benchmarks** (DA/CC, BASIX, Sydney Water typical ranges) and a **$/m² ceiling sanity-check** using the evidenced ~285 m² GFA — a natural Task 7 if desired; left out to keep Task 6 minimal.
- Whether **contingency** should be grossed up by GST at all in `_render_gst_basis` (a reserve, not a taxable supply) — minor, related to Task 3.
- The **legacy LLM-only** `create_cost_plan_instructions.md` path — not the generator for architect-pm projects; mirror these guardrails there only if non-hybrid projects start showing the same defects.
