from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ScenarioCommand(BaseModel):
    id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    expected: str = Field(min_length=1)


class RoleScenario(BaseModel):
    schema_version: int = 1
    role: str
    seed_profile: dict[str, Any]
    decisions: list[dict[str, Any]]
    files: list[str]
    quote_groups: list[list[str]]
    commands: list[ScenarioCommand] = Field(min_length=1)
    expected: dict[str, Any]
    forbidden: list[str] = Field(min_length=1)
    timing_boundaries: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self) -> "RoleScenario":
        command_ids = [command.id for command in self.commands]
        if len(command_ids) != len(set(command_ids)):
            raise ValueError("scenario command ids must be unique")
        if not {"building_class", "work_type", "user_role", "state"}.issubset(
            self.seed_profile
        ):
            raise ValueError("seed profile is missing a required capability field")
        return self


class PromptTurn(BaseModel):
    actor: str = Field(min_length=1)
    prompt: str = Field(min_length=1)


class PromptAssertion(BaseModel):
    layer: str = Field(min_length=1)
    target: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    expected: Any


class PromptScenario(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    risk_tags: list[str] = Field(min_length=1)
    channels: list[str] = Field(min_length=1)
    fixture_files: list[str] = Field(default_factory=list)
    setup: list[str] = Field(min_length=1)
    turns: list[PromptTurn] = Field(min_length=1)
    assertions: list[PromptAssertion] = Field(min_length=1)
    forbidden: list[str] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    plan_gates: list[str] = Field(min_length=1)


class PromptSuite(BaseModel):
    schema_version: int = 1
    suite: str = Field(min_length=1)
    scenarios: list[PromptScenario] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self) -> "PromptSuite":
        scenario_ids = [scenario.id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("prompt scenario ids must be unique")
        return self


def load_scenario(path: Path) -> RoleScenario:
    # JSON is valid YAML. Keeping manifests in this subset avoids a test-only parser.
    return RoleScenario.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_prompt_suite(path: Path) -> PromptSuite:
    # JSON is valid YAML. Keeping manifests in this subset avoids a test-only parser.
    return PromptSuite.model_validate(json.loads(path.read_text(encoding="utf-8")))


def assert_fixture_contract(scenario: RoleScenario, fixture_root: Path) -> None:
    missing = [name for name in scenario.files if not (fixture_root / name).is_file()]
    if missing:
        raise AssertionError(f"missing acceptance fixtures: {', '.join(missing)}")
    named_files = set(scenario.files)
    unknown_quote_files = {
        name
        for group in scenario.quote_groups
        for name in group
        if name not in named_files
    }
    if unknown_quote_files:
        raise AssertionError(
            f"quote groups reference unknown fixtures: {sorted(unknown_quote_files)}"
        )


def assert_prompt_suite_contract(suite: PromptSuite, fixture_root: Path) -> None:
    missing = {
        name
        for scenario in suite.scenarios
        for name in scenario.fixture_files
        if not (fixture_root / name).is_file()
    }
    if missing:
        raise AssertionError(f"missing prompt-suite fixtures: {sorted(missing)}")
