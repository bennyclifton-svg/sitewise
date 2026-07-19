import uuid

import pytest
from pydantic import ValidationError

from app.schemas.document_selections import ReplaceTenderQuoteSelection


def _group(name: str, *ids: uuid.UUID) -> dict:
    return {"builder_name": name, "ordered_workspace_file_ids": list(ids)}


def test_tender_selection_enforces_group_count_not_file_count() -> None:
    ids = [uuid.uuid4() for _ in range(5)]
    selection = ReplaceTenderQuoteSelection(
        expected_revision=0,
        quote_candidates=[_group("Builder A", *ids[:4]), _group("Builder B", ids[4])],
    )
    assert len(selection.quote_candidates) == 2
    assert len(selection.quote_candidates[0].ordered_workspace_file_ids) == 4


def test_tender_selection_rejects_cross_group_duplicate_file() -> None:
    shared = uuid.uuid4()
    with pytest.raises(ValidationError, match="only one quote group"):
        ReplaceTenderQuoteSelection(
            expected_revision=0,
            quote_candidates=[_group("Builder A", shared), _group("Builder B", shared)],
        )
