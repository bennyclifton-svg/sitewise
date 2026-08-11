from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.consultant_register import (
    apply_consultant_register_facts,
    consultant_appointment_rows,
    expand_discipline_lump,
)


def test_consultant_appointment_rows_from_shared_facts():
    project = Project(project_metadata={})
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="services-engineer-hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "discipline": "Services Engineer (Hydraulic)",
                "firm": "TDL Engineering Consulting Pty Ltd",
                "status": "Certificate/DCD on file; appointment unverified",
                "evidence_paths": [
                    "04-projects/demo/_inbox/Hydraulic Design Certificate.pdf"
                ],
            },
        ),
        source="evidence",
    )
    rows = consultant_appointment_rows(project)
    assert rows[0]["discipline"] == "Services Engineer (Hydraulic)"
    assert rows[0]["firm"] == "TDL Engineering Consulting Pty Ltd"


def test_expand_discipline_lump_splits_mosaic_style_bundle():
    assert expand_discipline_lump(
        "Structural / civil / geotech / facade / waterproof / fire"
    ) == [
        "Structural Engineer",
        "Civil Engineer",
        "Geotechnical Engineer",
        "Facade Engineer",
        "Waterproofing Consultant",
        "Fire Engineer",
    ]


def test_expand_discipline_lump_keeps_single_discipline():
    assert expand_discipline_lump("Structural Engineer") is None
    assert expand_discipline_lump("Services Engineer (Hydraulic)") is None


def test_apply_expands_mega_lump_into_individual_rows():
    project = Project(project_metadata={})
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="fire-engineer",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "discipline": "Fire Engineer",
                "firm": "Fire Safety Studio Pty Ltd",
                "status": "Certificate/DCD on file; appointment unverified",
                "evidence_paths": ["fire-cert.pdf"],
            },
        ),
        source="evidence",
    )
    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Architect | Roda Architects Pty Ltd |  | Report/drawings on file; appointment unverified | [7] |
| Structural / civil / geotech / facade / waterproof / fire |  |  | Assumption / Not evidenced | — |

## Next
"""
    patched = apply_consultant_register_facts(markdown, project=project)
    assert "Structural / civil / geotech / facade / waterproof / fire" not in patched
    assert "| Structural Engineer | TBC |  | Assumption / Not evidenced | — |" in patched
    assert "| Civil Engineer | TBC |  | Assumption / Not evidenced | — |" in patched
    assert "| Geotechnical Engineer | TBC |  | Assumption / Not evidenced | — |" in patched
    assert "| Facade Engineer | TBC |  | Assumption / Not evidenced | — |" in patched
    assert "| Waterproofing Consultant | TBC |  | Assumption / Not evidenced | — |" in patched
    assert (
        "| Fire Engineer | Fire Safety Studio Pty Ltd |  | "
        "Certificate/DCD on file; appointment unverified |"
    ) in patched


def test_apply_expands_mega_lump_without_shared_facts():
    project = Project(project_metadata={})
    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Facade / waterproofing / fire / vertical transport / landscape / traffic |  |  | Assumption / Not evidenced | — |

## Next
"""
    patched = apply_consultant_register_facts(markdown, project=project)
    assert "Facade / waterproofing / fire / vertical transport / landscape / traffic" not in patched
    assert "| Facade Engineer | TBC |" in patched
    assert "| Waterproofing Consultant | TBC |" in patched
    assert "| Fire Engineer | TBC |" in patched
    assert "| Vertical Transport Consultant | TBC |" in patched
    assert "| Landscape Architect | TBC |" in patched
    assert "| Traffic Engineer | TBC |" in patched


def test_apply_expands_services_lump_into_specialist_rows():
    project = Project(project_metadata={})
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="services-engineer-hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "discipline": "Services Engineer (Hydraulic)",
                "firm": "TDL Engineering Consulting Pty Ltd",
                "status": "Certificate/DCD on file; appointment unverified",
                "evidence_paths": ["hydraulic-cert.pdf"],
            },
        ),
        source="evidence",
    )
    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Services Engineer / hydraulic / mechanical / electrical |  |  | Assumption / Not evidenced | — |

## Next
"""
    patched = apply_consultant_register_facts(markdown, project=project)
    assert "Services Engineer / hydraulic / mechanical / electrical" not in patched
    assert "| Services Engineer (Hydraulic) | TDL Engineering Consulting Pty Ltd |" in patched
    assert "| Services Engineer (Mechanical) | TBC |" in patched
    assert "| Services Engineer (Electrical) | TBC |" in patched


def test_apply_consultant_register_facts_fills_blank_and_adds_missing_rows():
    project = Project(project_metadata={})
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="structural-engineer",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "discipline": "Structural Engineer",
                "firm": "Zait Engineering Solutions Pty Ltd",
                "status": "Report/drawings on file; appointment unverified",
                "evidence_paths": ["04-projects/demo/_inbox/S100-03.pdf"],
            },
        ),
        source="evidence",
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="fire-engineer",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "discipline": "Fire Engineer",
                "firm": "Fire Safety Studio Pty Ltd",
                "status": "Certificate/DCD on file; appointment unverified",
                "evidence_paths": [
                    "04-projects/demo/_inbox/Fire Wet & Dry Design Certificate.pdf"
                ],
            },
        ),
        source="evidence",
    )

    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Architect | Roda Architects Pty Ltd |  | Report/drawings on file; appointment unverified | [7] |
| Structural Engineer |  |  | Assumption / Not evidenced | — |
| Services Engineer / hydraulic / mechanical / electrical |  |  | Assumption / Not evidenced | — |

## Planning and Compliance
Body
"""
    citations = {
        "04-projects/demo/_inbox/S100-03.pdf": 9,
        "04-projects/demo/_inbox/Fire Wet & Dry Design Certificate.pdf": 10,
    }
    patched = apply_consultant_register_facts(
        markdown,
        project=project,
        citation_numbers=citations,
    )
    assert "Zait Engineering Solutions Pty Ltd" in patched
    assert "Fire Safety Studio Pty Ltd" in patched
    assert "Structural Engineer |" in patched
    assert (
        "| Structural Engineer | Zait Engineering Solutions Pty Ltd |" in patched
        or "| Structural Engineer | Zait Engineering Solutions Pty Ltd |"
        in patched.replace("  ", " ")
    )
    assert "Services Engineer / hydraulic / mechanical / electrical" not in patched
    assert "| Services Engineer (Hydraulic) |" in patched
    assert "| Services Engineer (Mechanical) |" in patched
    assert "| Services Engineer (Electrical) |" in patched
