from pathlib import Path

from app.sitewise.pmp_coverage import (
    COVERAGE_REGISTER_HEADING,
    backfill_corpus_coverage,
    build_corpus_coverage_requirements,
    corpus_coverage_violations,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MERIDIAN_DIR = REPO_ROOT / "data" / "synthetic-mobilisation-evidence" / "meridian-chambers-fitout"


def _meridian_files() -> tuple[list[str], list[str], list[str]]:
    paths = [
        "01-email-tenant-fitout-brief-to-landlord.md",
        "02-planning-advice-parramatta-ssd.md",
        "03-engagement-letter-form-function-studio.md",
        "04-fee-proposal-form-function-studio.md",
        "05-email-landlord-base-building-and-builder-rom.md",
    ]
    texts = [(MERIDIAN_DIR / path).read_text(encoding="utf-8") for path in paths]
    refs = [
        f"project_evidence:04-projects/meridian-chambers-fitout/_inbox/{path}#chunk={index}"
        for index, path in enumerate(paths, start=1)
    ]
    return texts, paths, refs


def test_meridian_coverage_requirements_capture_dates_values_and_scope() -> None:
    texts, labels, _refs = _meridian_files()

    requirement_text = "\n".join(
        requirement.fact
        for requirement in build_corpus_coverage_requirements(texts, labels)
    ).lower()

    assert "42 workstations" in requirement_text
    assert "8 partner offices" in requirement_text
    assert "4 x 8-person meeting rooms" in requirement_text
    assert "2 x 16-person meeting rooms" in requirement_text
    assert "1 november 2026" in requirement_text
    assert "$1.35m-$1.55m" in requirement_text
    assert "$180,000" in requirement_text
    assert "400 kva" in requirement_text and "500 kva" in requirement_text
    assert "22-26 weeks" in requirement_text
    assert "$180k-$240k" in requirement_text


_SPARSE_MARKDOWN = """
## Project snapshot

Evidence on file: planning advice, engagement letter, fee proposal.

## Scope and client requirements

The scope includes a commercial office fit-out with a legal library and partner offices.

## Compliance and approvals

SSD is the primary pathway.
"""


def test_meridian_coverage_rejects_missing_files_and_scope_facts() -> None:
    texts, labels, refs = _meridian_files()

    violations = corpus_coverage_violations(
        _SPARSE_MARKDOWN,
        output_evidence_refs=refs[:3],
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    )

    joined = "\n".join(violations).lower()
    assert "04-fee-proposal-form-function-studio.md" in joined
    assert "05-email-landlord-base-building-and-builder-rom.md" in joined
    assert "pmp evidence_refs is missing active project document" in joined
    assert "42 workstations" in joined
    assert "1 november 2026" in joined
    assert "$180,000" in joined
    assert "22-26 weeks" in joined


_COMPLETE_MARKDOWN = """
## Project snapshot

Evidence on file: all five Meridian current-corpus files.
Class 5 commercial office tower. SSD primary pathway; CDC not assumed.
Target possession 1 November 2026; rent-free period 1 February 2027 to 30 June 2027;
firm occupation 1 July 2027; target SSD lodgement September 2026;
SSD assessment 10-14 weeks; CC 4-6 weeks; occupancy load increases from 98 to 142 persons.

## Scope and client requirements

Scope: 180 m2 open-plan legal library, 42 workstations, 8 partner offices,
6 meeting rooms, 4 x 8-person meeting rooms, 2 x 16-person meeting rooms, 60-seat breakout,
secure records room and comms room, amenities 2 male, 2 female, 1 accessible WC
and shower on Level 4. Levels 2 and 5 remain partially occupied and after-hours
access is required. Level 4 mezzanine 185 m2. Budget aspiration $1.35M-$1.55M.

## Compliance and approvals

Maintain NABERS 4.5 stars. Supplementary sprinklers and tenant smoke control
remain tenant scope. Fire engineering performance solution required.
Tenant works cannot start until SSD consent and fit-out consent deed.

## Programme and milestones

Programme ROM 22-26 weeks. After-hours works 10:00 pm-6:00 am, no Sunday works.

## Cost and budget

Professional fee $118,500 ex GST; engagement dated 24 February 2026 and accepted
28/02/2026; fee proposal dated 10 February 2026; CA phase assumed 7 months.
Landlord HVAC contribution $180,000. Existing 400 kVA switchboard
upgrades to 500 kVA. ROM range $1,280,000 to $1,520,000. After-hours labour risk
$180k to $240k.

## Procurement and delivery

Two invited builders. Tender evaluation includes after-hours and services-capacity risk.
Architect-PM is not Superintendent, Certifier, PCA, or builder. Fortnightly reporting.
Core drilling 7am to 5pm. Acoustic partitions, landlord approval of slab penetrations,
and Apex is not a related party to Form & Function.
"""


def test_meridian_coverage_accepts_compact_fact_carriage() -> None:
    texts, labels, refs = _meridian_files()

    assert corpus_coverage_violations(
        _COMPLETE_MARKDOWN,
        output_evidence_refs=refs,
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    ) == []


def test_backfill_appends_register_and_clears_all_violations() -> None:
    texts, labels, refs = _meridian_files()

    result = backfill_corpus_coverage(
        _SPARSE_MARKDOWN,
        output_evidence_refs=refs[:3],
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    )

    assert f"## {COVERAGE_REGISTER_HEADING}" in result.markdown
    assert "42 workstations" in result.markdown
    assert result.backfilled_facts
    assert list(result.evidence_refs)[:3] == refs[:3]
    assert set(refs) <= set(result.evidence_refs)
    assert set(result.added_evidence_refs) == set(refs[3:])
    assert corpus_coverage_violations(
        result.markdown,
        output_evidence_refs=result.evidence_refs,
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    ) == []


def test_backfill_leaves_complete_draft_unchanged() -> None:
    texts, labels, refs = _meridian_files()
    markdown = _COMPLETE_MARKDOWN

    result = backfill_corpus_coverage(
        markdown,
        output_evidence_refs=refs,
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    )

    assert result.markdown == markdown
    assert not result.backfilled_facts
    assert not result.added_evidence_refs
    assert list(result.evidence_refs) == refs


def test_backfill_is_idempotent() -> None:
    texts, labels, refs = _meridian_files()

    first = backfill_corpus_coverage(
        _SPARSE_MARKDOWN,
        output_evidence_refs=refs[:3],
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    )
    second = backfill_corpus_coverage(
        first.markdown,
        output_evidence_refs=first.evidence_refs,
        required_evidence_refs=refs,
        source_texts=texts,
        source_labels=labels,
    )

    assert second.markdown == first.markdown
    assert second.markdown.count(f"## {COVERAGE_REGISTER_HEADING}") == 1
    assert not second.added_evidence_refs
