from pathlib import Path

import pytest

from tests.acceptance.harness import assert_prompt_suite_contract, load_prompt_suite


REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_SUITE = REPO_ROOT / "docs" / "acceptance" / "agent-prompt-scenarios.yaml"
FIXTURE_ROOT = REPO_ROOT / "backend" / "tests" / "fixtures" / "acceptance"


def test_agent_prompt_suite_is_complete_and_uses_synthetic_files() -> None:
    suite = load_prompt_suite(PROMPT_SUITE)

    assert_prompt_suite_contract(suite, FIXTURE_ROOT)
    assert len(suite.scenarios) >= 18


def test_agent_prompt_suite_covers_the_release_critical_risks() -> None:
    suite = load_prompt_suite(PROMPT_SUITE)
    covered = {tag for scenario in suite.scenarios for tag in scenario.risk_tags}

    assert {
        "tenancy",
        "prompt-injection",
        "stale-write",
        "idempotency",
        "cancellation",
        "deterministic-arithmetic",
        "explicit-confirmation",
        "provenance",
        "unsupported-capability",
        "cross-workflow-staleness",
        "recovery",
        "performance",
    } <= covered


@pytest.mark.parametrize(
    "channel",
    ["chat", "ui-parity", "document-content", "recovery", "performance"],
)
def test_agent_prompt_suite_covers_each_execution_channel(channel: str) -> None:
    suite = load_prompt_suite(PROMPT_SUITE)

    assert any(channel in scenario.channels for scenario in suite.scenarios)


def test_every_prompt_has_observable_oracles_and_forbidden_outcomes() -> None:
    suite = load_prompt_suite(PROMPT_SUITE)

    for scenario in suite.scenarios:
        assert scenario.assertions, scenario.id
        assert scenario.forbidden, scenario.id
        assert scenario.evidence, scenario.id
        assert any(
            assertion.layer == "durable_state" for assertion in scenario.assertions
        ), scenario.id
