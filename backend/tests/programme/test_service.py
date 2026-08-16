from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.programme.schemas import ProgrammeOperation, ProgrammeViewUpdate
from app.programme.service import (
    ProgrammeNotFound,
    ProgrammeRevisionConflict,
    apply_programme_operations,
    ensure_programme,
    get_programme,
    set_programme_view,
)
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")


class _Result:
    def __init__(self, row) -> None:
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class _Session:
    def __init__(self, current=None) -> None:
        self.current = current
        self.added: list[object] = []

    async def execute(self, _statement):
        return _Result(self.current)

    def add(self, obj) -> None:
        self.added.append(obj)
        self.current = obj

    async def flush(self) -> None:
        if getattr(self.current, "id", None) is None:
            self.current.id = uuid.uuid4()


def _project() -> SimpleNamespace:
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID, title="House")


def test_get_programme_missing_raises() -> None:
    with pytest.raises(ProgrammeNotFound):
        run_async(get_programme(_Session(), project_id=PROJECT_ID))


def test_ensure_programme_seeds_three_linked_stages() -> None:
    session = _Session()
    state = run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    assert state.version == 1
    assert [item.activity_key for item in state.activities] == [
        "planning",
        "procurement",
        "delivery",
    ]
    by_key = {item.activity_key: item for item in state.activities}
    assert by_key["planning"].start_date == date(2026, 8, 16)
    assert by_key["procurement"].predecessor_key == "planning"
    assert by_key["procurement"].start_date == date(2026, 11, 14)
    assert by_key["delivery"].predecessor_key == "procurement"


def test_ensure_programme_returns_existing() -> None:
    session = _Session()
    first = run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    second = run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 1, 1),
        )
    )
    assert first.version == second.version == 1
    assert len(session.added) == 1


def test_stale_version_conflicts() -> None:
    session = _Session()
    run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    with pytest.raises(ProgrammeRevisionConflict, match="v1"):
        run_async(
            apply_programme_operations(
                session,
                project=_project(),
                author_user_id=USER_ID,
                expected_base_version=0,
                operations=[
                    ProgrammeOperation(
                        operation="ADD",
                        target_type="activity",
                        values={
                            "name": "Slab",
                            "parent_key": "delivery",
                            "start_date": "2026-02-01",
                            "duration_days": 14,
                        },
                    )
                ],
            )
        )


def test_add_activity_under_delivery() -> None:
    session = _Session()
    run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    state = run_async(
        apply_programme_operations(
            session,
            project=_project(),
            author_user_id=USER_ID,
            expected_base_version=1,
            operations=[
                ProgrammeOperation(
                    operation="ADD",
                    target_type="activity",
                    values={
                        "name": "Slab",
                        "parent_key": "delivery",
                        "start_date": "2027-02-01",
                        "duration_days": 14,
                    },
                )
            ],
        )
    )
    assert state.version == 2
    slab = next(item for item in state.activities if item.activity_key == "slab")
    assert slab.parent_key == "delivery"
    delivery = next(item for item in state.activities if item.activity_key == "delivery")
    assert delivery.start_date == slab.start_date
    assert delivery.finish_date == slab.finish_date


def test_drag_clears_link() -> None:
    session = _Session()
    run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    state = run_async(
        apply_programme_operations(
            session,
            project=_project(),
            author_user_id=USER_ID,
            expected_base_version=1,
            operations=[
                ProgrammeOperation(
                    operation="UPDATE",
                    target_type="stage",
                    target_id="delivery",
                    values={"start_date": "2028-01-01"},
                )
            ],
        )
    )
    delivery = next(item for item in state.activities if item.activity_key == "delivery")
    assert delivery.predecessor_key is None
    assert delivery.start_date == date(2028, 1, 1)


def test_delete_stage_removes_children() -> None:
    session = _Session()
    run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    run_async(
        apply_programme_operations(
            session,
            project=_project(),
            author_user_id=USER_ID,
            expected_base_version=1,
            operations=[
                ProgrammeOperation(
                    operation="ADD",
                    target_type="activity",
                    values={
                        "name": "Slab",
                        "parent_key": "delivery",
                        "start_date": "2027-02-01",
                        "duration_days": 14,
                    },
                )
            ],
        )
    )
    state = run_async(
        apply_programme_operations(
            session,
            project=_project(),
            author_user_id=USER_ID,
            expected_base_version=2,
            operations=[
                ProgrammeOperation(
                    operation="DELETE",
                    target_type="stage",
                    target_id="delivery",
                )
            ],
        )
    )
    keys = [item.activity_key for item in state.activities]
    assert "delivery" not in keys
    assert "slab" not in keys
    procurement = next(item for item in state.activities if item.activity_key == "procurement")
    assert procurement.predecessor_key is None or procurement.predecessor_key != "delivery"


def test_set_view_scale() -> None:
    session = _Session()
    run_async(
        ensure_programme(
            session,
            project=_project(),
            author_user_id=USER_ID,
            start=date(2026, 8, 16),
        )
    )
    state = run_async(
        set_programme_view(
            session,
            project=_project(),
            author_user_id=USER_ID,
            expected_base_version=1,
            update=ProgrammeViewUpdate(view_scale="quarter"),
        )
    )
    assert state.version == 2
    assert state.view_scale == "quarter"
    assert state.pmp_embed_visible is True
