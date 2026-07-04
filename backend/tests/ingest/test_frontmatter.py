from pathlib import Path

from ingest.extractors.base import ExtractedDocument
from ingest.frontmatter import parse_frontmatter
from ingest.metadata import infer_project_context
from ingest.persist import _merged_metadata
from ingest.router import build_ingest_plan
from ingest.types import ManifestEntry

SEED_CONTENT = """---
tier: topic
seed_type: cost-reference
loaded_by: task subject (cost, budget, contingency, claim, variation pricing)
applies_to_roles: [owner-builder, architect-pm, builder, d-and-c]
state_default: NSW
topics: [cost, budget, contingency]
summary: "Residential cost-management conventions."
required_by: {create-pmp: 3, create-cost-plan: 1}
doctrine_anchors: [§seed-consultation-discipline, §evidence-discipline]
---

# Cost Management Principles — Residential

Body content.
"""


def test_parse_frontmatter_reads_seed_contract_fields() -> None:
    frontmatter = parse_frontmatter(SEED_CONTENT)

    assert frontmatter["tier"] == "topic"
    assert frontmatter["topics"] == ["cost", "budget", "contingency"]
    assert frontmatter["required_by"] == {"create-pmp": 3, "create-cost-plan": 1}
    assert frontmatter["applies_to_roles"] == [
        "owner-builder",
        "architect-pm",
        "builder",
        "d-and-c",
    ]
    assert frontmatter["doctrine_anchors"][0] == "§seed-consultation-discipline"
    assert frontmatter["summary"] == "Residential cost-management conventions."


def test_parse_frontmatter_without_block_returns_empty() -> None:
    assert parse_frontmatter("# Heading\n\nBody with --- rule later\n---\n") == {}


def test_parse_frontmatter_unclosed_block_returns_empty() -> None:
    assert parse_frontmatter("---\ntier: topic\n# never closed") == {}


def test_parse_frontmatter_invalid_yaml_returns_empty() -> None:
    assert parse_frontmatter("---\ntier: [unclosed\n---\nbody") == {}


def test_parse_frontmatter_non_mapping_returns_empty() -> None:
    assert parse_frontmatter("---\n- a\n- b\n---\nbody") == {}


def test_parse_frontmatter_converts_dates_to_strings() -> None:
    frontmatter = parse_frontmatter("---\ndate: 2026-05-30\nstatus: reference\n---\nbody")

    assert frontmatter["date"] == "2026-05-30"
    assert frontmatter["status"] == "reference"


def _entry(relative_path: str) -> ManifestEntry:
    name = relative_path.rsplit("/", maxsplit=1)[-1]
    return ManifestEntry(
        absolute_path=Path(relative_path),
        relative_path=relative_path,
        project=relative_path.split("/", maxsplit=1)[0],
        filename=name,
        extension=Path(name).suffix.lower(),
        size_bytes=100,
    )


def _plan_for(relative_path: str):
    from ingest.classify import classify_entry

    entry = _entry(relative_path)
    context = infer_project_context(entry.relative_path)
    return build_ingest_plan(entry, context, classify_entry(entry))


def test_merged_metadata_persists_frontmatter_for_platform_seed() -> None:
    plan = _plan_for("seed/cost-management-principles.md")
    extracted = ExtractedDocument(normalized_content=SEED_CONTENT)

    metadata = _merged_metadata(plan, extracted)

    assert metadata["knowledge_scope"] == "platform"
    assert metadata["frontmatter"]["tier"] == "topic"
    assert metadata["frontmatter"]["required_by"] == {"create-pmp": 3, "create-cost-plan": 1}


def test_merged_metadata_skips_frontmatter_for_project_evidence() -> None:
    plan = _plan_for("delivery-demo/08-meetings-reporting/minutes.md")
    extracted = ExtractedDocument(normalized_content=SEED_CONTENT)

    metadata = _merged_metadata(plan, extracted)

    assert "frontmatter" not in metadata
