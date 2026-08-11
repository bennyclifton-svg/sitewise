import uuid
from datetime import UTC, datetime

from app.database.project import Project
from app.projects.generation_context import FieldState, resolve_project_generation_context
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.schemas.project_snapshot import ProjectSnapshot

PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime(2026, 8, 10, tzinfo=UTC),
            "content_fingerprint": "a" * 64,
            "context_version": 7,
            "field_states": {},
            "identity": {
                "project_id": str(PROJECT_ID),
                "title": "Representative project",
                "slug": "representative-project",
                "workspace_path": "04-projects/representative-project",
                "phase": "procurement",
                "status": "active",
                "site_address": {
                    "status": "confirmed",
                    "value": "10 Test Street",
                    "source": "project_setup",
                },
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": str(PROJECT_ID),
                "profile_revision": 3,
                "building_class": "residential",
                "work_type": "new",
                "subclasses": ["apartments"],
                "scale": {},
                "complexity": {"planning": "da"},
                "work_scope": ["hydraulic_plumbing", "electrical_power", "substructure"],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 2, "items": []},
            "evidence": {
                "fingerprint": "b" * 64,
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


def test_generation_context_exposes_evidence_derived_consultant_appointments() -> None:
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
                "evidence_paths": ["04-projects/demo/03-design/hydraulic/H-001.pdf"],
            },
        ),
        source="evidence",
    )

    context = resolve_project_generation_context(_snapshot(), project=project)

    appointments = context.stakeholders["consultant_appointments"]
    assert appointments.state == FieldState.KNOWN
    assert appointments.source == "evidence"
    assert appointments.value[0]["firm"] == "TDL Engineering Consulting Pty Ltd"
    assert appointments.value[0]["discipline"] == "Services Engineer (Hydraulic)"
