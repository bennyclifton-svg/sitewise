import time

from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
from app.sitewise.cost_plan_evidence_validation import cost_plan_evidence_grounded_violations
from app.sitewise.cost_plan_renderer import render_cost_plan_scaffold
from app.sitewise.cost_plan_sources import required_section_headings
from tests.sitewise.test_cost_plan_evidence import FIXTURE_DIR
from tests.sitewise.test_pmp_renderer import _harrison_clarke_project


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _pack():
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
        _read("03-owner-project-brief-chen-residence.md"),
        _read("09-planning-pathway-memo-harrison-clarke.md"),
        _read("06-geotechnical-report-terratech.md"),
        _read("11-master-programme-chen-residence.md"),
        _read("12-certifier-appointment-chen-residence.md"),
    ]
    return extract_cost_plan_evidence_pack(texts, ["ref:a", "ref:b", "ref:c", "ref:d", "ref:e", "ref:f", "ref:g"])


def test_render_cost_plan_scaffold_includes_all_sections() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    headings = {
        line.strip()[3:].strip().lower()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    }
    for heading in required_section_headings("architect-pm"):
        assert heading.lower() in headings


def test_render_cost_plan_scaffold_surfaces_owner_brief_ceiling() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "1,850,000" in markdown
    assert "120,000" in markdown
    assert "148,500" in markdown
    assert "chen residence" in markdown or "14 wattle grove" in markdown
    assert "| section | evidence status | ref |" in markdown
    assert "- **facts**" in markdown
    assert "da and cc authority fees" in markdown
    assert "geotechnical engineer" in markdown
    assert "kitchen joinery pc" in markdown
    assert "indicative total project cost" in markdown
    assert "inc gst" in markdown
    assert "owner-held contingency" in markdown
    assert "pendant lights: $8,000 ex gst (owner-supplied)" in markdown
    assert "$$" not in markdown


def test_render_cost_plan_scaffold_fee_stages_have_single_dollar_prefix() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    assert "| Mobilisation & concept | Engagement signed | $22,000 |" in markdown
    assert "$$" not in markdown


def test_render_cost_plan_scaffold_passes_evidence_validation() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    violations = cost_plan_evidence_grounded_violations(
        markdown,
        _pack().evidence_refs,
        source_texts=[_read("03-owner-project-brief-chen-residence.md")],
    )
    assert violations == []


def test_render_cost_plan_scaffold_is_fast() -> None:
    project = _harrison_clarke_project()
    pack = _pack()
    start = time.perf_counter()
    for _ in range(20):
        render_cost_plan_scaffold(project, pack, "evidence_grounded")
    elapsed_ms = (time.perf_counter() - start) * 1000 / 20
    assert elapsed_ms < 500


def test_audit_assumptions_never_claims_none_when_breakdown_has_assumptions() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "assumption: none identified" not in markdown
    assert "none identified beyond construction tender pricing" not in markdown
    assert "construction trade pricing" in markdown
    assert "consultant fees" in markdown


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
    assert grand != 2_148_500
