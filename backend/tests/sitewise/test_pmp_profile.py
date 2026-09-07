import uuid

from app.schemas.projects import ProjectProfileView
from app.projects.artefact_blocks import materialize_block_identity
from app.sitewise.pmp_profile import apply_profile_basis, profile_basis_rows


def test_every_populated_profile_value_is_preserved_and_conflicts_are_visible():
    profile = ProjectProfileView(
        project_id=uuid.uuid4(),
        profile_revision=5,
        title="Test House",
        building_class="residential",
        work_type="new",
        subclasses=["house"],
        scale={"gfa_sqm": 220, "storeys": 2, "bedrooms": 4, "site_sqm": 450},
        complexity={
            "planning": "cdc",
            "contamination_level": "nil",
            "procurement_route": "traditional",
        },
        work_scope=["demolition", "decontamination", "vertical_transport"],
        scope_narrative=["Keep oak | tree\n<script>"],
        budget="800000",
        state="NSW",
    )
    original = profile.model_dump()
    result = apply_profile_basis(
        "# Project Management Plan\n\n## Scope\nHouse.", profile
    )
    assert "| scale / gfa sqm | 220 | Project Summary |" in result
    assert "| budget | 800000 | Cost Planning |" in result
    assert "Keep oak \\| tree &lt;script&gt;" in result
    assert "contamination is recorded as nil" in result
    assert "Confirm whether a lift" in result
    assert len(profile_basis_rows(profile)) == 17
    assert profile.model_dump() == original
    profile.budget = "850000"
    refreshed = apply_profile_basis(result, profile)
    assert "800000" not in refreshed
    assert refreshed.count("## Profile basis") == 1
    assert "850000" in refreshed
    stamped = materialize_block_identity(result, actor_source="system").markdown
    refreshed_stamped = apply_profile_basis(stamped, profile)
    assert "800000" not in refreshed_stamped
    assert refreshed_stamped.count("## Profile basis") == 1


def test_zero_and_false_are_not_silently_dropped():
    profile = ProjectProfileView(
        project_id=uuid.uuid4(),
        profile_revision=1,
        scale={"amount": 0, "enabled": False},
    )
    assert {row[1] for row in profile_basis_rows(profile)} == {"0", "False"}
