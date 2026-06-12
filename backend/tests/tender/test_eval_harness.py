import pytest

from tender.eval.golden import DEFAULT_MANIFEST_PATH
from tender.eval.harness import run_eval


@pytest.mark.tender_eval
def test_tender_eval_harness_runs_with_empty_golden_set() -> None:
    result = run_eval(DEFAULT_MANIFEST_PATH)

    assert result.summary["documents_evaluated"] == 0
    assert result.documents == ()
    assert "overall" in result.summary
    assert result.summary["overall"]["extraction"]["line_item_gold_count"] == 0

