from __future__ import annotations

from tender.schemas import ProjectContext
from tender.services.silence import (
    SilenceBenchmark,
    SilenceCell,
    SilenceLineItem,
    SilenceMappedCell,
    SilenceSynonym,
    assemble_evidence_packet,
)


def test_packet_short_circuits_on_explicit_exclusion_match() -> None:
    packet = assemble_evidence_packet(
        cell=SilenceCell(
            code="03.05",
            name="Retaining walls",
            expected_because=("SITE.RETAINING.SHOULD",),
            synonyms=(SilenceSynonym("retaining walls"),),
        ),
        context=_context(slope_class="steep"),
        line_items=(
            SilenceLineItem(
                id="line-1",
                description="Retaining walls",
                item_status="excluded",
                page_ref={"doc": "quote-a", "page": 7},
            ),
        ),
    )

    assert packet.explicit_exclusion is not None
    assert packet.explicit_exclusion["line_item_id"] == "line-1"
    assert packet.packet["explicit_exclusions"] == [
        {
            "line_item_id": "line-1",
            "description": "Retaining walls",
            "similarity": 1.0,
            "page_ref": {"doc": "quote-a", "page": 7},
        }
    ]


def test_packet_collects_ps_candidates_by_embedding_similarity() -> None:
    packet = assemble_evidence_packet(
        cell=SilenceCell(
            code="03.05",
            name="Retaining walls",
            expected_because=("SITE.RETAINING.SHOULD",),
            synonyms=(SilenceSynonym("retaining walls", embedding=(1.0, 0.0)),),
        ),
        context=_context(slope_class="steep"),
        line_items=(
            SilenceLineItem(
                id="ps-1",
                description="Provisional sum - site works",
                item_status="ps_allowance",
                allowance_cents=2_500_000,
                embedding=(0.92, 0.08),
                page_ref={"doc": "quote-a", "page": 4},
            ),
        ),
        ps_similarity_threshold=0.60,
    )

    assert packet.packet["candidate_ps_lines"] == [
        {
            "line_item_id": "ps-1",
            "description": "Provisional sum - site works",
            "allowance_cents": 2_500_000,
            "similarity": packet.packet["candidate_ps_lines"][0]["similarity"],
            "page_ref": {"doc": "quote-a", "page": 4},
        }
    ]
    assert packet.packet["candidate_ps_lines"][0]["similarity"] > 0.99


def test_packet_records_bundling_headroom_and_missing_benchmarks() -> None:
    cell = SilenceCell(
        code="03.05",
        name="Retaining walls",
        expected_because=("SITE.RETAINING.SHOULD",),
        synonyms=(SilenceSynonym("retaining walls"),),
        bundling_parents=("03.01",),
        benchmark_key="site.retaining",
    )
    cells_by_code = {
        "03.01": SilenceCell(
            code="03.01",
            name="Site costs allowance",
            expected_because=(),
            benchmark_key="site.allowance_lump",
        ),
        "03.05": cell,
    }

    packet = assemble_evidence_packet(
        cell=cell,
        context=_context(slope_class="steep"),
        line_items=(),
        mapped_cells=(SilenceMappedCell("03.01", amount_cents=4_800_000),),
        cells_by_code=cells_by_code,
        benchmarks=(
            SilenceBenchmark(
                benchmark_key="site.allowance_lump",
                state="NSW",
                region="metro",
                build_type="new_build",
                spec_level="builder_base",
                p50_cents=3_500_000,
            ),
        ),
    )

    assert packet.packet["bundling_parents_present"] == [
        {
            "cell": "03.01",
            "quote_amount_cents": 4_800_000,
            "benchmark_p50_parent_cents": 3_500_000,
            "benchmark_p50_this_cell_cents": None,
            "headroom_assessment": "unknown headroom",
        }
    ]


def test_packet_marks_not_required_candidate_when_applicability_is_false() -> None:
    packet = assemble_evidence_packet(
        cell=SilenceCell(
            code="03.05",
            name="Retaining walls",
            expected_because=("SITE.RETAINING.SHOULD",),
            applicability={"field": "slope_class", "in": ["moderate", "steep"]},
        ),
        context=_context(slope_class="flat"),
        line_items=(),
    )

    assert packet.packet["context_signals"]["slope_class"] == "flat"
    assert packet.packet["context_signals"]["soil_class"] == "H2"
    assert packet.packet["not_required_candidate"] is True
    assert packet.packet["allowed_outcomes"] == [
        "excluded",
        "bundled",
        "ps_covered",
        "not_required",
        "ambiguous",
    ]


def _context(**overrides: object) -> ProjectContext:
    data = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 1,
        "soil_class": "H2",
        "slope_class": "flat",
        "bal_rating": "none",
        "spec_level": "builder_base",
    }
    data.update(overrides)
    return ProjectContext.model_validate(data)
