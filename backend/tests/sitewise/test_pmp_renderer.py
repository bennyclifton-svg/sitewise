import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.database.project import Project
from app.sitewise.mobilisation_evidence import extract_mobilisation_evidence_pack
from app.sitewise.pmp_evidence_validation import evidence_grounded_violations
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.pmp_sources import required_section_headings
from app.workflows.create_pmp import markdown_section_headings

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "chen-residence"
ENGAGEMENT_FIXTURE = FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md"
FEE_FIXTURE = FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md"

ENGAGEMENT_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "01-engagement-letter-harrison-clarke-studio.md#chunk=abc"
)
FEE_REF = (
    "project_evidence:04-projects/test/02-consultant/architect/"
    "02-fee-proposal-harrison-clarke-studio.md#chunk=def"
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _harrison_clarke_project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="test-project-112",
        title="Chen Residence",
        workspace_path="04-projects/test-project-112",
        phase="brief-planning",
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata=None,
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )


def _harrison_clarke_pack():
    source_texts = [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]
    return extract_mobilisation_evidence_pack(source_texts, [ENGAGEMENT_REF, FEE_REF])


def _render_harrison_clarke_scaffold() -> str:
    return render_pmp_scaffold(
        _harrison_clarke_project(),
        _harrison_clarke_pack(),
        "evidence_grounded",
    )


def test_render_pmp_scaffold_includes_all_architect_pm_sections() -> None:
    markdown = _render_harrison_clarke_scaffold()
    assert markdown.startswith("# Project Management Plan")
    assert markdown_section_headings(markdown) == list(required_section_headings("architect-pm"))


def test_render_pmp_scaffold_surfaces_harrison_clarke_pack_facts() -> None:
    markdown = _render_harrison_clarke_scaffold().lower()

    assert "michael and sarah chen" in markdown
    assert "wattle grove" in markdown
    assert "148,500" in markdown
    assert "september 2026" in markdown  # Chen's evidenced DA target
    assert "linden constructions" in markdown  # Chen's evidenced conflicting party
    assert "executed 16/05/2026" in markdown
    assert "qbe australia ltd" in markdown
    assert "cdc not assumed" in markdown


def _walsh_project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="walsh-renovation",
        title="Walsh Renovation",
        workspace_path="04-projects/walsh-renovation",
        phase="brief-planning",
        archetype="renovation",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata=None,
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )


def _walsh_pack():
    walsh_dir = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "walsh-renovation"
    paths = sorted(walsh_dir.glob("[0-9]*.md"))
    source_texts = [p.read_text(encoding="utf-8") for p in paths]
    return extract_mobilisation_evidence_pack(source_texts, source_labels=[p.name for p in paths])


def test_render_pmp_scaffold_walsh_has_no_fabricated_entities() -> None:
    """Walsh evidence names Atelier North, no conflict, July 2026 — none of Chen's defaults."""
    markdown = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded")
    lowered = markdown.lower()

    assert "hcs" not in lowered  # firm is Atelier North, not the Chen sample
    assert "linden constructions" not in lowered  # no such party in evidence
    assert "september 2026" not in lowered  # Walsh DA target is July 2026
    assert "atelier north" in lowered
    assert "july 2026" in lowered


def test_render_pmp_scaffold_walsh_uses_renovation_risk_set() -> None:
    """Renovation must carry its evidenced risks, not the greenfield reactive-soil set."""
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()

    assert "reactive soil" not in md  # greenfield-only risk
    assert "latent conditions in existing footings" in md
    assert "live occupation — dust" in md
    assert "conservation-area controls" in md


def test_render_pmp_scaffold_walsh_geotech_is_owner_commissioned() -> None:
    """Engagement excludes specialist reports — architect coordinates, owner commissions."""
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()
    assert "coordinate owner's appointment" in md


def test_render_pmp_scaffold_walsh_reporting_cadence_is_fortnightly() -> None:
    """Communications cadence must reflect the engagement (fortnightly), not default monthly."""
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()
    assert "fortnightly owner progress reporting" in md
    assert "owner update cadence: monthly progress reporting" not in md


def test_render_pmp_scaffold_walsh_promotes_heritage_advice() -> None:
    """Heritage desktop advice must become concrete PMP actions, not a generic risk word."""
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()

    assert "contributory building in conservation area" in md
    assert "not individually listed" in md
    assert "front facade and roof form should be retained and repaired" in md
    assert "set back 3 m" in md
    assert "heritage impact statement" in md
    assert "6" in md and "8 weeks" in md


def test_render_pmp_scaffold_walsh_promotes_owner_brief_and_builder_rom_detail() -> None:
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()

    assert "$85,000 additional contingency" in md
    assert "north-facing courtyard" in md
    assert "front parlour" in md
    assert "early 2027" in md
    assert "18 months" in md
    assert "14" in md and "16 months" in md
    assert "party wall tie-in" in md
    assert "$25" in md and "40k" in md
    assert "not related parties" in md


def test_render_pmp_scaffold_walsh_includes_fact_ledger() -> None:
    md = render_pmp_scaffold(_walsh_project(), _walsh_pack(), "evidence_grounded").lower()

    assert "- **fact ledger**" in md
    assert "03-owner-project-brief-walsh-house.md" in md
    assert "05-email-heritage-advisor-desktop.md" in md
    assert "front facade and roof form" in md


def test_render_pmp_scaffold_reuses_greenfield_due_diligence_checklist() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "### Due diligence checklist (open until evidenced) — new-dwelling" in markdown
    assert "Survey / title boundary" in markdown
    assert "Geotechnical / AS 2870 class" in markdown
    assert "Include this table under **Approvals and compliance**" not in markdown


def test_render_pmp_scaffold_evidence_on_file_uses_single_bullet_prefix() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "- Engagement letter (Harrison Clarke Studio Pty Ltd)" in markdown
    assert "- - Engagement letter" not in markdown


def test_render_pmp_scaffold_fee_proposal_date_from_fee_document() -> None:
    texts = [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]
    pack = extract_mobilisation_evidence_pack(texts, [ENGAGEMENT_REF, FEE_REF])
    markdown = render_pmp_scaffold(_harrison_clarke_project(), pack, "evidence_grounded")

    assert "Fee proposal — dated 28 April 2026" in markdown
    assert pack.fee_proposal_date == "28 April 2026"


def test_render_pmp_scaffold_chen_stage1_upgrades_brief_and_budget() -> None:
    texts = [
        (FIXTURE_DIR / name).read_text(encoding="utf-8")
        for name in (
            "01-engagement-letter-harrison-clarke-studio.md",
            "02-fee-proposal-harrison-clarke-studio.md",
            "03-owner-project-brief-chen-residence.md",
            "04-email-thread-brief-signoff.md",
        )
    ]
    pack = extract_mobilisation_evidence_pack(texts, [ENGAGEMENT_REF, FEE_REF])
    markdown = render_pmp_scaffold(_harrison_clarke_project(), pack, "evidence_grounded")

    assert pack.owner_brief_on_file is True
    assert pack.construction_budget_ceiling == "$1,850,000"
    assert "Owner project brief" in markdown
    assert "pending owner formal sign-off" not in markdown.lower()
    assert "| Construction budget | Grounded | owner project brief |" in markdown
    assert "| Owner project brief sign-off | Grounded | owner project brief |" in markdown
    assert "$1,850,000" in markdown
    assert "Construction budget not evidenced" not in markdown
    assert "CA phase assumed 12 months" in markdown
    assert "Construction budget not evidenced | Owner |" not in markdown
    assert "double garage.." not in markdown
    assert "Brief signed on file.." not in markdown
    assert "September 2026** (engagement letter); brief signed on file." in markdown
    assert "Owner project brief signed 12 May 2026." in markdown
    assert "Construction budget confirmed $1,850,000 working ceiling." in markdown


def test_render_pmp_scaffold_includes_programme_submilestone_table() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "| Sub-milestone | Maps to stage | Status | Note |" in markdown
    assert "Slab / substructure" in markdown
    assert "Lockup" in markdown


def test_render_pmp_scaffold_includes_nsw_basix_authority_row() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "| BASIX (commitment) | Assumption | Owner / Architect-PM |" in markdown


def test_render_pmp_scaffold_includes_risk_table_skeleton() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "| Risk | Owner | Status | Next action | Due |" in markdown
    assert "Planning pathway / DA programme slip" in markdown


def test_render_pmp_scaffold_internal_audit_facts_from_pack() -> None:
    markdown = _render_harrison_clarke_scaffold()

    assert "- **Facts**" in markdown
    assert "engagement executed 16/05/2026" in markdown.lower()
    assert "148,500" in markdown
    assert "- **Judgements**" in markdown
    assert "pending narrative generation" in markdown.lower()


def test_render_pmp_scaffold_passes_structure_validation() -> None:
    markdown = _render_harrison_clarke_scaffold()
    violations = greenfield_structure_violations(
        markdown,
        archetype="new-dwelling",
        user_role="architect-pm",
    )
    assert violations == []


def test_render_pmp_scaffold_passes_core_evidence_validation() -> None:
    markdown = _render_harrison_clarke_scaffold()
    source_texts = [
        ENGAGEMENT_FIXTURE.read_text(encoding="utf-8"),
        FEE_FIXTURE.read_text(encoding="utf-8"),
    ]
    violations = evidence_grounded_violations(
        markdown,
        [ENGAGEMENT_REF, FEE_REF],
        source_texts=source_texts,
    )
    assert violations == []


def test_render_pmp_scaffold_rejects_platform_seeded_mode() -> None:
    try:
        render_pmp_scaffold(
            _harrison_clarke_project(),
            _harrison_clarke_pack(),
            "platform_seeded",
        )
    except ValueError as exc:
        assert "evidence_grounded" in str(exc)
    else:
        raise AssertionError("Expected ValueError for platform_seeded mode")


def test_render_pmp_scaffold_is_fast() -> None:
    project = _harrison_clarke_project()
    pack = _harrison_clarke_pack()
    start = time.perf_counter()
    for _ in range(20):
        render_pmp_scaffold(project, pack, "evidence_grounded")
    elapsed_ms = (time.perf_counter() - start) / 20 * 1000
    assert elapsed_ms < 500
