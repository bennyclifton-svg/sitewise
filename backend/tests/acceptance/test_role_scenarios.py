from pathlib import Path

import pytest

from tests.acceptance.harness import assert_fixture_contract, load_scenario


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_ROOT = REPO_ROOT / "docs" / "acceptance" / "role-scenarios"
FIXTURE_ROOT = REPO_ROOT / "backend" / "tests" / "fixtures" / "acceptance"


@pytest.mark.parametrize(
    "name",
    ["construction-manager", "architect", "design-manager"],
)
def test_role_scenario_manifest_is_complete_and_uses_synthetic_files(name: str) -> None:
    scenario = load_scenario(MANIFEST_ROOT / f"{name}.yaml")

    assert scenario.role == name
    assert_fixture_contract(scenario, FIXTURE_ROOT)
    assert "cross_project_read" in scenario.forbidden
    assert "cross_project_write" in scenario.forbidden
    assert all(command.expected for command in scenario.commands)


def test_every_role_reads_the_shared_project_intelligence() -> None:
    scenarios = [load_scenario(path) for path in sorted(MANIFEST_ROOT.glob("*.yaml"))]

    for scenario in scenarios:
        tools = {command.tool for command in scenario.commands}
        assert tools & {"get_project_snapshot", "get_project_next_actions"}
