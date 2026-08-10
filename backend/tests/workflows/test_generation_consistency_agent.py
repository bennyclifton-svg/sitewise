from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.assistant.pmp_models import resolve_pmp_model
from app.projects.artefact_context import RfpContext
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import ContextField
from app.workflows.generation_consistency import SemanticCandidate
from app.workflows.generation_consistency_agent import (
    ConsistencyResolutionOutput,
    resolve_consistency_candidates,
)
from tests.conftest import run_async


def test_resolver_sends_one_typed_call_with_verified_brief_and_candidate_batch() -> (
    None
):
    brief = _brief()
    candidates = (
        _candidate(
            "scope:0:0:1:0",
            kind="possible_duplicate_scope",
            excerpts=(
                "Coordinate structural design.",
                "Coordinate the structural design.",
            ),
        ),
        _candidate(
            "risk:0:0:1:0",
            kind="possible_duplicate_risk",
            excerpts=("Late authority approval.", "Authority approval may be late."),
        ),
    )
    calls: list[tuple[str, str]] = []

    async def runner(_agent, prompt: str, *, model: str):
        calls.append((prompt, model))
        return SimpleNamespace(
            output=ConsistencyResolutionOutput(
                confirmed_candidate_ids=[candidates[0].id]
            )
        )

    with patch(
        "app.workflows.generation_consistency_agent.run_agent_with_retry",
        new=runner,
    ):
        resolved = run_async(resolve_consistency_candidates(brief, candidates))

    assert resolved == {candidates[0].id}
    assert len(calls) == 1
    prompt, model = calls[0]
    assert model == resolve_pmp_model().execution_id
    assert brief.input_fingerprint in prompt
    assert "Harbour Office Upgrade" in prompt
    for candidate in candidates:
        assert candidate.id in prompt
        assert candidate.kind in prompt
        assert all(excerpt in prompt for excerpt in candidate.excerpts)


def test_resolver_filters_ids_that_were_not_supplied() -> None:
    brief = _brief()
    candidate = _candidate(
        "scope:0:0:1:0",
        kind="possible_duplicate_scope",
        excerpts=("Coordinate structural design.", "Coordinate the structural design."),
    )

    async def runner(_agent, _prompt: str, *, model: str):
        del model
        return SimpleNamespace(
            output=ConsistencyResolutionOutput(
                confirmed_candidate_ids=[candidate.id, "hallucinated:candidate"]
            )
        )

    with patch(
        "app.workflows.generation_consistency_agent.run_agent_with_retry",
        new=runner,
    ):
        resolved = run_async(resolve_consistency_candidates(brief, (candidate,)))

    assert resolved == {candidate.id}


def _brief():
    context = RfpContext(
        project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        context_version=7,
        discipline="Structural Engineer",
        identity={"title": _field("title", "Harbour Office Upgrade")},
        taxonomy={},
        scope={},
        scale={},
        complexity={},
        programme={},
        procurement={},
        approvals={},
        stakeholders={},
        derived_risks=[],
        section_weights={},
        critical_unknowns=[],
    )
    return build_generation_brief(
        context,
        evidence_refs=["project/brief.md"],
        constraints=["Resolve only genuinely duplicated content."],
    )


def _field(key: str, value: str) -> ContextField:
    return ContextField(key=key, label=key.title(), state="known", value=value)


def _candidate(
    candidate_id: str,
    *,
    kind: str,
    excerpts: tuple[str, ...],
) -> SemanticCandidate:
    return SemanticCandidate(
        id=candidate_id,
        kind=kind,
        section_keys=("first", "second"),
        excerpts=excerpts,
    )
