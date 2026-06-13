from __future__ import annotations

import uuid

import pytest

from tender import worker
from tender.llm.client import LLMAdjudicationResponse
from tender.models import TenderCellStatus
from tender.schemas import ProjectContext
from tender.services import silence
from tests.conftest import run_async


@pytest.mark.parametrize(
    ("outcome", "stored_status"),
    [
        ("bundled", "bundled"),
        ("ps_covered", "ps"),
        ("not_required", "not_required"),
        ("ambiguous", "silent_ambiguous"),
    ],
)
def test_adjudicated_outcomes_map_to_internal_statuses(
    outcome: str, stored_status: str
) -> None:
    row = _status_row()

    decision = run_async(
        silence.adjudicate_silence_packet(
            _packet(),
            _context(),
            llm_client=FakeSilenceClient(outcome, confidence=0.96),
        )
    )
    silence.apply_silence_decision(row, decision)

    assert row.status == stored_status
    assert row.qa_state == "needs_review"
    assert row.evidence["packet"] == _packet().packet
    assert row.evidence["adjudication"]["outcome"] == outcome


def test_excluded_from_adjudication_is_downgraded_to_ambiguous_needs_review() -> None:
    row = _status_row()

    decision = run_async(
        silence.adjudicate_silence_packet(
            _packet(),
            _context(),
            llm_client=FakeSilenceClient("excluded", confidence=0.99),
        )
    )
    silence.apply_silence_decision(row, decision)

    assert row.status == "silent_ambiguous"
    assert row.qa_state == "needs_review"
    assert row.evidence["adjudication"]["outcome"] == "excluded"
    assert row.evidence["adjudication"]["stored_status"] == "silent_ambiguous"
    assert row.evidence["adjudication"]["downgraded"] is True


def test_silence_decisions_never_auto_pass_even_when_confident() -> None:
    decision = run_async(
        silence.adjudicate_silence_packet(
            _packet(),
            _context(),
            llm_client=FakeSilenceClient("bundled", confidence=0.99),
        )
    )

    assert decision.status == "bundled"
    assert decision.qa_state == "needs_review"
    assert decision.confidence == 0.99


def test_explicit_exclusion_short_circuit_skips_llm() -> None:
    row = _status_row()
    packet = silence.EvidencePacket(
        packet={
            **_packet().packet,
            "explicit_exclusions": [
                {
                    "line_item_id": "line-1",
                    "description": "Retaining walls",
                    "similarity": 1.0,
                    "page_ref": {"doc": "quote-a", "page": 7},
                }
            ],
        },
        explicit_exclusion={
            "line_item_id": "line-1",
            "description": "Retaining walls",
            "similarity": 1.0,
            "page_ref": {"doc": "quote-a", "page": 7},
        },
    )

    decision = run_async(
        silence.infer_silence_from_packet(
            row,
            packet,
            _context(),
            llm_client=ExplodingSilenceClient(),
        )
    )

    assert decision.status == "excluded_explicit"
    assert row.status == "excluded_explicit"
    assert row.qa_state == "needs_review"
    assert row.evidence["adjudication"]["source"] == "explicit_exclusion_match"
    assert row.evidence["adjudication"]["cites"] == ["line-1"]


def test_adjudication_stores_full_packet_and_metadata() -> None:
    row = _status_row()

    decision = run_async(
        silence.adjudicate_silence_packet(
            _packet(),
            _context(),
            llm_client=FakeSilenceClient("bundled", confidence=0.82),
        )
    )
    silence.apply_silence_decision(row, decision)

    assert row.evidence == {
        "packet": _packet().packet,
        "adjudication": {
            "outcome": "bundled",
            "stored_status": "bundled",
            "confidence": 0.82,
            "rationale": "fake rationale",
            "model": "fake-model",
            "prompt_version": "0.1.0",
            "request_id": "fake-request",
            "cites": [],
            "downgraded": False,
            "review_reason": "silence_never_auto_pass_v1",
        },
    }


def test_worker_registers_infer_silence_handler() -> None:
    assert worker.HANDLERS["infer_silence"] is silence.infer_silence


class FakeSilenceClient:
    def __init__(self, outcome: str, *, confidence: float) -> None:
        self.outcome = outcome
        self.confidence = confidence
        self.calls = 0

    async def adjudicate(self, question, choices, evidence, context, *, prompt_version, model_key):
        self.calls += 1
        assert choices == silence.ALLOWED_OUTCOMES
        assert evidence == _packet().packet
        assert prompt_version == "0.1.0"
        assert model_key == "tender_model_adjudicate_small"
        return LLMAdjudicationResponse(
            choice=self.outcome,
            confidence=self.confidence,
            rationale="fake rationale",
            model="fake-model",
            prompt_version=prompt_version,
            request_id="fake-request",
        )


class ExplodingSilenceClient:
    async def adjudicate(self, *args, **kwargs):
        raise AssertionError("LLM should not be called for explicit exclusions")


def _packet() -> silence.EvidencePacket:
    return silence.EvidencePacket(
        packet={
            "cell": {
                "code": "03.05",
                "name": "Retaining walls",
                "expected_because": ["SITE.RETAINING.SHOULD"],
            },
            "explicit_exclusions": [],
            "candidate_ps_lines": [],
            "bundling_parents_present": [{"cell": "03.01"}],
            "context_signals": {"slope_class": "steep", "soil_class": "H2"},
            "not_required_candidate": False,
            "allowed_outcomes": silence.ALLOWED_OUTCOMES,
        }
    )


def _status_row() -> TenderCellStatus:
    return TenderCellStatus(
        id=uuid.uuid4(),
        comparison_id=uuid.uuid4(),
        quote_id=uuid.uuid4(),
        cell_code="03.05",
        status="silent_ambiguous",
        evidence={"expected_because": ["SITE.RETAINING.SHOULD"]},
        qa_state="needs_review",
    )


def _context() -> ProjectContext:
    return ProjectContext.model_validate(
        {
            "state": "NSW",
            "region": "metro",
            "build_type": "new_build",
            "dwelling_class": "class_1a",
            "storeys": 1,
            "soil_class": "H2",
            "slope_class": "steep",
            "bal_rating": "none",
            "spec_level": "builder_base",
        }
    )
