from ingest.types import Classification

from app.intake.classifier import filing_destination

PROJECT = "04-projects/greenfield-demo"


def _classification(
    document_class: str,
    subject: str = "none",
    **metadata: str,
) -> Classification:
    return Classification(
        document_class=document_class,  # type: ignore[arg-type]
        ingest_mode="full_text",
        document_subject=subject,  # type: ignore[arg-type]
        document_metadata=metadata,
        confidence=0.9,
        basis="filename",
    )


def _destination(classification: Classification, filename: str = "file.pdf") -> str | None:
    return filing_destination(
        classification,
        workspace_path=f"{PROJECT}/_inbox/{filename}",
        filename=filename,
        project_workspace_path=PROJECT,
    )


def test_routes_every_class_subject_pair() -> None:
    expected = {
        ("commercial", "cost"): "01-cost",
        ("commercial", "contract_admin"): "01-cost/variations",
        ("report", "structural"): "03-design/structural",
        ("report", "geotechnical"): "03-design/01-due-diligence",
        ("report", "surveyor"): "03-design/01-due-diligence",
        ("report", "heritage"): "03-design/01-due-diligence",
        ("report", "town_planner"): "04-planning-and-authorities",
        ("certificate", "town_planner"): "04-planning-and-authorities",
        ("schedule", "programme"): "06-programme",
        ("schedule", "cost"): "01-cost",
        ("drawing", "architect"): "03-design/architect",
        ("report", "architect"): "03-design/architect",
        ("specification", "architect"): "03-design/architect",
        ("drawing", "mechanical"): "03-design/mechanical",
    }
    for (document_class, subject), folder in expected.items():
        assert _destination(_classification(document_class, subject)) == folder, (
            document_class,
            subject,
        )


def test_routes_by_class() -> None:
    assert _destination(_classification("statutory_instrument")) == "04-planning-and-authorities"
    assert _destination(_classification("certificate")) == "04-planning-and-authorities"
    assert _destination(_classification("contract")) == "02-consultant"
    assert _destination(_classification("correspondence")) == "08-meetings-reporting"
    assert _destination(_classification("photo")) == "07-construction/photos"


def test_procurement_stage_overrides_class_routing() -> None:
    classification = _classification(
        "commercial",
        "cost",
        procurement_stage="rft",
    )
    assert _destination(classification) == "05-procurement"


def test_unknown_without_discipline_is_unresolved() -> None:
    assert _destination(_classification("unknown")) is None


def test_inbox_package_beats_classification() -> None:
    """A user who dropped a file in _inbox/STRUCTURAL/ meant it."""
    destination = filing_destination(
        _classification("commercial", "cost"),
        workspace_path=f"{PROJECT}/_inbox/STRUCTURAL/invoice.pdf",
        filename="invoice.pdf",
        project_workspace_path=PROJECT,
    )
    assert destination == "03-design/structural"


def test_fee_proposal_routes_to_consultant_discipline() -> None:
    classification = _classification(
        "commercial",
        commercial_type="fee_proposal",
        discipline="architect",
    )
    assert _destination(classification) == "02-consultant/architect"


def test_quote_routes_to_procurement_quotes() -> None:
    classification = _classification("commercial", commercial_type="quote")
    assert _destination(classification) == "05-procurement/quotes"


def test_brief_kind_routes_to_brief_pmp() -> None:
    classification = _classification("report", brief_kind="project_brief")
    assert _destination(classification) == "00-brief-pmp"


def test_due_diligence_flag_routes_to_due_diligence_folder() -> None:
    classification = _classification("report", due_diligence="true")
    assert _destination(classification) == "03-design/01-due-diligence"


def test_stale_commercial_type_does_not_route_an_overridden_report() -> None:
    """Preserved metadata from a superseded class must not outrank the user's class."""
    classification = _classification(
        "report",
        "heritage",
        commercial_type="fee_proposal",
        discipline="structural",
        procurement_stage="rft",
    )
    assert _destination(classification) == "03-design/01-due-diligence"
