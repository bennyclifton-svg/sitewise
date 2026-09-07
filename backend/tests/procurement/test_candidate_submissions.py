import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.procurement.candidate_submissions import resolve_submission_files
from app.procurement.strategy import ProcurementStrategyValidationError
from tests.conftest import run_async


def test_link_rejects_file_outside_project():
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: [])
            )
        )
    )
    with pytest.raises(ProcurementStrategyValidationError, match="project"):
        run_async(
            resolve_submission_files(
                session, project_id=uuid.uuid4(), file_ids=[uuid.uuid4()]
            )
        )


def test_multiple_supporting_files_keep_requested_order():
    first, second = uuid.uuid4(), uuid.uuid4()
    files = [
        SimpleNamespace(
            id=value,
            filename="quote.pdf",
            storage_key="project/quote.pdf",
            content_hash=str(value),
            size_bytes=200,
        )
        for value in [second, first]
    ]
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                scalars=lambda: SimpleNamespace(all=lambda: files)
            )
        )
    )
    actual = run_async(
        resolve_submission_files(
            session, project_id=uuid.uuid4(), file_ids=[first, second]
        )
    )
    assert [item.id for item in actual] == [first, second]


def test_duplicate_selection_is_rejected():
    value = uuid.uuid4()
    with pytest.raises(ProcurementStrategyValidationError, match="unique"):
        run_async(
            resolve_submission_files(
                None, project_id=uuid.uuid4(), file_ids=[value, value]
            )
        )
