from types import SimpleNamespace
import uuid

from app.projects.identity import (
    classification_summary,
    identity_from_evidence_texts,
    resolve_project_identity,
)


def test_identity_from_evidence_extracts_australian_address() -> None:
    identity = identity_from_evidence_texts(
        [
            "Project brief — proposed new dwelling at "
            "14 Wattle Grove, Lindfield NSW 2070"
        ]
    )

    assert identity["site_address"] == "14 Wattle Grove, Lindfield NSW 2070"


def test_resolve_prefers_profile_over_evidence() -> None:
    project = SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=1,
        building_class="residential",
        work_type="new",
        user_role="architect-pm",
        state="NSW",
        project_metadata={
            "taxonomy": {
                "site_address": "82 Queen Street, Petersham NSW 2049",
                "client": "Profile Client",
            }
        },
    )
    evidence = [
        {
            "snippet": (
                "proposed new dwelling at 14 Wattle Grove, Lindfield NSW 2070"
            )
        }
    ]

    identity = resolve_project_identity(project, evidence=evidence)

    assert identity["site_address"] == "82 Queen Street, Petersham NSW 2049"
    assert identity["client"] == "Profile Client"
    assert identity["site_address_source"] == "profile"


def test_classification_summary_includes_scale() -> None:
    project = SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=1,
        building_class="residential",
        work_type="refurb",
        user_role="architect-pm",
        state="NSW",
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "scale": {"site_sqm": 450, "gfa_sqm": 280, "storeys": 2},
                "complexity": {},
                "work_scope": [],
            }
        },
    )

    assert classification_summary(project) == (
        "residential / refurb / house / 450 m² site / 280 m² GFA / 2 storeys"
    )
