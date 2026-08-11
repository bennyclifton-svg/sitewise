from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.consultant_facts import (
    evidence_status_for_kind,
    map_discipline_to_register_label,
    reconcile_consultant_facts_from_documents,
    upsert_consultant_fact_from_document,
)
from app.projects.project_knowledge import list_shared_project_objects


def test_map_discipline_to_register_label_normalizes_services_aliases():
    assert map_discipline_to_register_label("Hydraulic") == "Services Engineer (Hydraulic)"
    assert (
        map_discipline_to_register_label("Electrical")
        == "Services Engineer (Electrical)"
    )
    assert map_discipline_to_register_label("Structural") == "Structural Engineer"
    assert map_discipline_to_register_label("Acoustic") == "Acoustic Consultant"
    assert map_discipline_to_register_label("Fire") == "Fire Engineer"


def test_upsert_consultant_fact_from_document_metadata():
    project = Project(project_metadata={})
    document = SourceDocument(
        filename="Hydraulic Design Certificate.pdf",
        relative_path="04-projects/demo/_inbox/Hydraulic Design Certificate.pdf",
        document_metadata={
            "discipline": "Hydraulic",
            "issuing_firm": "TDL Engineering Consulting Pty Ltd",
        },
        normalized_content="",
        project="demo",
        phase="brief-planning",
        document_class="certificate",
    )

    fact = upsert_consultant_fact_from_document(project, document)

    assert fact is not None
    assert fact.value["firm"] == "TDL Engineering Consulting Pty Ltd"
    assert fact.value["discipline"] == "Services Engineer (Hydraulic)"
    assert fact.value["status"] == evidence_status_for_kind("certificate")
    assert document.relative_path in fact.value["evidence_paths"]


def test_reconcile_merges_same_discipline_firm_and_skips_empty():
    project = Project(project_metadata={})
    docs = [
        SourceDocument(
            filename="H-001.pdf",
            relative_path="04-projects/demo/_inbox/H-001.pdf",
            document_metadata={
                "discipline": "Hydraulic",
                "issuing_firm": "TDL Engineering Consulting Pty Ltd",
            },
            normalized_content="",
            project="demo",
            phase="brief-planning",
            document_class="drawing",
        ),
        SourceDocument(
            filename="Hydraulic Design Certificate.pdf",
            relative_path="04-projects/demo/_inbox/Hydraulic Design Certificate.pdf",
            document_metadata={
                "discipline": "Hydraulic",
                "issuing_firm": "TDL Engineering Consulting Pty Ltd",
            },
            normalized_content="",
            project="demo",
            phase="brief-planning",
            document_class="certificate",
        ),
        SourceDocument(
            filename="E00.pdf",
            relative_path="04-projects/demo/_inbox/E00.pdf",
            document_metadata={"discipline": "Electrical"},
            normalized_content="",
            project="demo",
            phase="brief-planning",
            document_class="drawing",
        ),
    ]

    updated = reconcile_consultant_facts_from_documents(project, docs)
    facts = list_shared_project_objects(project, kind="consultant")

    assert len(updated) == 1
    assert len(facts) == 1
    assert facts[0].value["firm"] == "TDL Engineering Consulting Pty Ltd"
    assert len(facts[0].value["evidence_paths"]) == 2
    # Certificate evidence is stronger than a layout sheet.
    assert facts[0].value["status"] == evidence_status_for_kind("certificate")
