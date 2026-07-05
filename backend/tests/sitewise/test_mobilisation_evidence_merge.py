from app.sitewise.mobilisation_evidence import (
    GAP_CONSTRUCTION_BUDGET,
    GAP_ENGAGEMENT,
    MobilisationEvidencePack,
    merge_evidence_packs,
)


def test_merge_evidence_packs_prefers_incoming_scalars_and_unions_lists() -> None:
    base = MobilisationEvidencePack(
        owners="Michael Chen",
        site_address="1 Old Street",
        scope_bullets=["Initial scope"],
        evidence_refs=["project_evidence:old.md#chunk=1"],
        gaps=[GAP_ENGAGEMENT, GAP_CONSTRUCTION_BUDGET],
    )
    incoming = MobilisationEvidencePack(
        site_address="14 Wattle Grove, Lindfield NSW 2070",
        appointee="Harrison Clarke Studio Pty Ltd",
        scope_bullets=["DA lodgement support"],
        evidence_refs=["project_evidence:new.md#chunk=2"],
        gaps=[GAP_CONSTRUCTION_BUDGET],
    )

    merged = merge_evidence_packs(base, incoming)

    assert merged.owners == "Michael Chen"
    assert merged.site_address == "14 Wattle Grove, Lindfield NSW 2070"
    assert merged.appointee == "Harrison Clarke Studio Pty Ltd"
    assert merged.scope_bullets == ["Initial scope", "DA lodgement support"]
    assert merged.evidence_refs == [
        "project_evidence:old.md#chunk=1",
        "project_evidence:new.md#chunk=2",
    ]
    assert GAP_ENGAGEMENT not in merged.gaps
