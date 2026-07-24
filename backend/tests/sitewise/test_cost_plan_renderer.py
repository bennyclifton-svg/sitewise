import time
from datetime import datetime, timezone

from app.database.project import Project
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack, extract_cost_plan_evidence_pack
from app.sitewise.cost_plan_evidence_validation import cost_plan_evidence_grounded_violations
from app.sitewise.cost_plan_renderer import render_cost_plan_scaffold
from app.sitewise.cost_plan_sources import required_section_headings
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from tests.sitewise.test_cost_plan_evidence import FIXTURE_DIR
from tests.sitewise.test_pmp_renderer import (
    PROJECT_ID,
    USER_ID,
    REPO_ROOT,
    _harrison_clarke_project,
    _walsh_project,
)


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


def _walsh_cost_pack():
    walsh_dir = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "walsh-renovation"
    paths = sorted(walsh_dir.glob("[0-9]*.md"))
    texts = [path.read_text(encoding="utf-8") for path in paths]
    refs = [f"ref:{path.name}" for path in paths]
    return extract_cost_plan_evidence_pack(texts, refs)


def _warehouse_project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="eastern-creek-distribution-centre",
        title="Eastern Creek Distribution Centre",
        workspace_path="04-projects/eastern-creek-distribution-centre",
        phase="brief-planning",
        archetype=None,
        building_class="industrial",
        work_type="new",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={"taxonomy": {"subclasses": ["warehouse"]}},
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def _warehouse_cost_pack() -> CostPlanEvidencePack:
    mobilisation = MobilisationEvidencePack(
        owners="Southern Logistics Holdings Pty Ltd",
        site_address="12 Distribution Drive, Eastern Creek NSW 2766",
        appointee="Meridian Industrial Architects Pty Ltd",
        fee_total_ex_gst="$185,000",
        engagement_executed_date="12/03/2026",
        gaps=[
            "Geotechnical report",
            "Certifier appointment",
            "Master programme on file",
            "Owner project brief formal sign-off",
            "Construction budget",
        ],
        evidence_refs=["ref:a"],
    )
    return CostPlanEvidencePack(
        mobilisation=mobilisation,
        project_name="Eastern Creek Distribution Centre",
        construction_budget_ceiling="$6,200,000",
        contingency_amount="$310,000",
        contingency_percent="5",
        owner_brief_on_file=True,
        evidence_refs=["ref:a"],
    )


def test_render_cost_plan_scaffold_includes_all_sections() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    headings = {
        line.strip()[3:].strip().lower()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    }
    for heading in required_section_headings("architect-pm"):
        assert heading.lower() in headings


def test_rendered_cost_plan_is_compact_and_uses_numbered_evidence_citations() -> None:
    markdown = render_cost_plan_scaffold(
        _harrison_clarke_project(), _pack(), "evidence_grounded"
    )
    headings = [
        line.strip()[3:].strip()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    ]

    assert headings == list(required_section_headings("architect-pm"))
    assert len(headings) == 5
    assert headings[-1] == "Source evidence and audit trail"
    assert "[1]" in markdown
    assert "### Citation key" in markdown
    assert len(markdown.split()) <= 1_400


def test_render_cost_plan_scaffold_surfaces_owner_brief_ceiling() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "1,850,000" in markdown
    assert "120,000" in markdown
    assert "148,500" in markdown
    assert "chen residence" in markdown or "14 wattle grove" in markdown
    assert "| cost-plan area | evidence status | ref |" in markdown
    assert "- **facts**" in markdown
    assert "da and cc authority fees" in markdown
    assert "geotechnical engineer" in markdown
    assert "kitchen joinery pc" in markdown
    assert "indicative total project cost" in markdown
    assert "inc gst" in markdown
    assert "owner-held contingency" in markdown
    assert "pendant lights" in markdown
    assert "$$" not in markdown


def test_render_cost_plan_scaffold_walsh_surfaces_all_cost_drivers() -> None:
    project = _walsh_project()
    project.building_class = "residential"
    project.work_type = "refurb"
    markdown = render_cost_plan_scaffold(project, _walsh_cost_pack(), "evidence_grounded")
    lowered = markdown.lower()

    assert "atelier north" in lowered
    assert "hcs architect" not in lowered
    assert "**profile:** residential / refurb, architect-pm, nsw" in lowered
    assert "$96,500" in markdown
    assert "$980,000 ex GST** is **outside" not in markdown
    assert "$920,000" in markdown
    assert "$85,000" in markdown
    assert "$880,000" in markdown and "$980,000" in markdown
    assert "not a tender" in lowered
    assert "heritage impact statement" in lowered
    assert "6-8 weeks" in lowered or "6–8 weeks" in lowered


def test_certifier_row_is_grounded_when_appointed() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "principal certifier | tbc | assumption | not yet appointed" not in markdown
    assert "$6,800" in markdown
    assert "certify nsw" in markdown


def test_owner_supplied_items_do_not_assert_gst_basis() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded").lower()
    assert "$33,000 inc gst" not in markdown
    assert "owner-supplied allowances inc gst" not in markdown
    assert "gst basis not stated" in markdown


def test_render_cost_plan_scaffold_fee_stages_have_single_dollar_prefix() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    assert "$148,500 | Locked |" in markdown
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
        if s.startswith("## ") and s[3:].strip() == "budget reconciliation and cost breakdown":
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


def test_construction_rows_benchmarked_to_ceiling() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")
    section = _breakdown_section(markdown)
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


NO_RATE_PACK_DISCLOSURE = (
    "No NSW industrial rate pack exists yet — this is a structure-only scaffold; "
    "every construction line is a lump-sum TBC pending head-builder tender."
)


def test_render_cost_plan_scaffold_industrial_warehouse_uses_industrial_taxonomy() -> None:
    markdown = render_cost_plan_scaffold(
        _warehouse_project(), _warehouse_cost_pack(), "evidence_grounded"
    )

    headings = {
        line.strip()[3:].strip().lower()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    }
    for heading in required_section_headings("architect-pm"):
        assert heading.lower() in headings

    assert "Structural steel and frame" in markdown
    assert "Dock hardstand and yard" in markdown
    assert "Kitchen and bathrooms" not in markdown
    assert "BASIX" not in markdown
    assert NO_RATE_PACK_DISCLOSURE in markdown


def test_render_cost_plan_scaffold_residential_still_uses_residential_taxonomy() -> None:
    markdown = render_cost_plan_scaffold(_harrison_clarke_project(), _pack(), "evidence_grounded")

    assert "Kitchen and bathrooms" in markdown
    assert "BASIX" in markdown
    assert "Structural steel and frame" not in markdown
    assert "Dock hardstand and yard" not in markdown
    assert NO_RATE_PACK_DISCLOSURE not in markdown


def test_render_cost_plan_scaffold_walsh_residential_still_uses_residential_taxonomy() -> None:
    project = _walsh_project()
    project.building_class = "residential"
    project.work_type = "refurb"
    markdown = render_cost_plan_scaffold(project, _walsh_cost_pack(), "evidence_grounded")

    assert "Kitchen and bathrooms" in markdown
    assert "BASIX" in markdown
    assert NO_RATE_PACK_DISCLOSURE not in markdown
