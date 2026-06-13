from __future__ import annotations

from pathlib import Path

import yaml

from tender import worker
from tender.models import FLAG_TYPES
from tender.services import analysis
from tender.services.analysis import AnalysisCell, AnalysisFlagDraft, AnalysisQuote, build_question_list


def test_every_flag_type_has_question_template_from_seed_language() -> None:
    templates = _templates()
    flags = [
        AnalysisFlagDraft(
            comparison_id="comparison",
            quote_id="quote-a",
            cell_code="18.01",
            flag_type=flag_type,
            severity="warning",
            headline_key=f"flag_phrases.{flag_type}",
            detail_key=None,
            evidence={"allowance_cents": 123_456},
        )
        for flag_type in FLAG_TYPES
    ]

    questions = build_question_list(
        flags,
        quotes=[AnalysisQuote("quote-a", "A Homes", 1_000_000)],
        cells=[AnalysisCell("18.01", "Cooktop", "cooktop")],
        question_templates=templates,
    )

    assert [question.flag_type for question in questions] == list(FLAG_TYPES)
    for question in questions:
        assert question.question == templates[question.flag_type].format(
            builder_name="A Homes",
            cell_name="Cooktop",
            amount="$1,234.56",
        )


def test_question_list_uses_only_warning_and_caution_unsuppressed_report_flags() -> None:
    templates = _templates()
    questions = build_question_list(
        [
            _flag("low_pc_allowance", "info"),
            _flag("unrealistic_ps", "caution", include_in_report=False),
            _flag("gap", "warning", qa_state="suppressed"),
            _flag("scope_ambiguity", "caution"),
        ],
        quotes=[AnalysisQuote("quote-a", "A Homes", 1_000_000)],
        cells=[AnalysisCell("18.01", "Cooktop", "cooktop")],
        question_templates=templates,
    )

    assert len(questions) == 1
    assert questions[0].flag_type == "scope_ambiguity"


def test_analysis_module_does_not_hardcode_report_phrasing() -> None:
    source = Path(analysis.__file__).read_text(encoding="utf-8")

    assert "Please confirm" not in source
    assert "No benchmark available" not in source
    assert "worth querying" not in source


def test_worker_registers_analysis_handlers() -> None:
    assert worker.HANDLERS["run_analysis"] is analysis.run_analysis
    assert worker.HANDLERS["generate_flags"] is analysis.generate_flags


def _flag(
    flag_type: str,
    severity: str,
    *,
    include_in_report: bool = True,
    qa_state: str = "needs_review",
) -> AnalysisFlagDraft:
    return AnalysisFlagDraft(
        comparison_id="comparison",
        quote_id="quote-a",
        cell_code="18.01",
        flag_type=flag_type,
        severity=severity,
        headline_key=f"flag_phrases.{flag_type}",
        detail_key=None,
        evidence={"allowance_cents": 123_456},
        include_in_report=include_in_report,
        qa_state=qa_state,
    )


def _templates() -> dict[str, str]:
    path = Path(__file__).resolve().parents[3] / "data" / "tender" / "report_language.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["question_templates"]
