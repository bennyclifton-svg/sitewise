from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.pmp_similarity import (
    PAIRWISE_SIMILARITY_LIMIT,
    below_pairwise_similarity_gate,
    identical_line_similarity,
)
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context

REPO_ROOT = Path(__file__).resolve().parents[3]
WAVE2_ARTEFACTS = (
    REPO_ROOT / "docs" / "plans" / "test-prompt-corpus" / "runs" / "artefacts"
)


def _markdown(name: str) -> str:
    return (WAVE2_ARTEFACTS / name).read_text(encoding="utf-8")


def _project(
    *,
    title: str,
    building_class: str,
    work_type: str,
    subclasses: list[str],
    budget: str,
    scale: dict | None = None,
    scope_narrative: list[str] | None = None,
    complexity: Mapping[str, str] | None = None,
    work_scope: list[str] | None = None,
):
    taxonomy: dict = {
        "subclasses": subclasses,
        "budget": budget,
        "scale": scale or {},
        "complexity": dict(complexity or {}),
        "work_scope": work_scope or [],
        "scope_narrative": scope_narrative or [],
    }
    return SimpleNamespace(
        slug=title.lower().replace(" ", "-"),
        title=title,
        workspace_path="04-projects/similarity-gate",
        phase="brief-planning",
        archetype=None,
        building_class=building_class,
        work_type=work_type,
        state="NSW",
        project_metadata={"taxonomy": taxonomy},
    )


def test_identical_line_similarity_is_one_for_the_same_document() -> None:
    markdown = "# PMP\n\n## Brief\nHeritage conservation area.\n"
    assert identical_line_similarity(markdown, markdown) == 1.0


def test_identical_line_similarity_ignores_clerk_block_comments() -> None:
    left = "| Address | Not provided |  |<!-- clerk:block id=aaa -->\n"
    right = "| Address | Not provided |  |<!-- clerk:block id=bbb -->\n"
    assert identical_line_similarity(left, right) == 1.0


def test_wave2_14_versus_43_is_the_similarity_defect_the_gate_catches() -> None:
    left = _markdown("w2-14.1-house-extension--create_pmp__v1.md")
    right = _markdown("w2-43.1-solar-battery--create_pmp__v1.md")
    score = identical_line_similarity(left, right)
    assert round(score, 3) == 0.947
    assert score >= PAIRWISE_SIMILARITY_LIMIT
    assert below_pairwise_similarity_gate(left, right) is False


def test_distinct_short_documents_pass_the_pairwise_gate() -> None:
    left = "# PMP\n\n## Brief\nSecond storey addition in Newtown.\n"
    right = "# PMP\n\n## Brief\nRooftop solar on a live distribution centre.\n"
    assert identical_line_similarity(left, right) < PAIRWISE_SIMILARITY_LIMIT
    assert below_pairwise_similarity_gate(left, right) is True


def test_scaffold_pair_differs_in_class_work_type_and_band() -> None:
    house = _project(
        title="14.1 House, extension and addition",
        building_class="residential",
        work_type="extend",
        subclasses=["house"],
        budget="around $750k",
        scale={"storeys": 2, "bedrooms": 2},
        scope_narrative=[
            "Second storey addition and rear extension to a semi in Newtown",
            "Heritage conservation area",
            "Adding 2 beds and a bathroom up, opening the rear to a new kitchen and living",
            "Clients living elsewhere during works",
        ],
    )
    solar = _project(
        title="43.1 Industrial other — solar and battery on existing site",
        building_class="infrastructure",
        work_type="new",
        subclasses=["energy_renewables"],
        budget="$4m",
        scale={"capacity_mw": 2, "battery_storage_mwh": 1},
        scope_narrative=[
            "Installing 2MW rooftop solar plus a 1MWh battery on an existing distribution centre",
            "Site operational",
        ],
    )
    house_ctx = pmp_taxonomy_context(house)
    solar_ctx = pmp_taxonomy_context(solar)
    assert house_ctx is not None and solar_ctx is not None
    assert house_ctx.building_class != solar_ctx.building_class
    assert house_ctx.work_type != solar_ctx.work_type
    assert house_ctx.scale_band != solar_ctx.scale_band
    assert house_ctx.scale_band == "s"
    assert solar_ctx.scale_band == "m"

    pack = MobilisationEvidencePack()
    left = render_pmp_scaffold(house, pack, "platform_seeded")
    right = render_pmp_scaffold(solar, pack, "platform_seeded")
    score = identical_line_similarity(left, right)
    assert 0.0 <= score <= 1.0
    # R1/R2 should pull this under the gate; Wave 2's live pair was 94.7%.
    assert score < 0.947
