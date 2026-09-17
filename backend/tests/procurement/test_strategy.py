import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.database.procurement_strategy import (
    ProcurementStrategy,
    ProcurementStrategyCandidate,
    ProcurementStrategyRow,
)
from app.procurement import strategy as service
from app.database.workspace_file import WorkspaceFile
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STRATEGY_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ROW_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.deleted = []

    def add(self, value) -> None:
        self.added.append(value)

    async def delete(self, value) -> None:
        self.deleted.append(value)

    async def flush(self) -> None:
        return None


class _ScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _ScalarRowsResult:
    def scalars(self):
        return []


class _EnsureSession:
    def __init__(self) -> None:
        self.strategy = None
        self.flush_count = 0

    def add(self, value) -> None:
        self.strategy = value

    async def flush(self) -> None:
        self.flush_count += 1
        assert self.strategy is not None
        assert self.strategy.__dict__.get("rows"), (
            "strategy rows must be attached before the strategy's first flush"
        )


def _strategy(*, revision: int = 1, locked: bool = False) -> ProcurementStrategy:
    now = datetime(2026, 8, 22, tzinfo=UTC)
    strategy = ProcurementStrategy(
        id=STRATEGY_ID,
        project_id=PROJECT_ID,
        revision=revision,
        tenderer_column_count=3,
        source_fingerprint="fingerprint",
        created_at=now,
        updated_at=now,
    )
    strategy.rows = [
        ProcurementStrategyRow(
            id=ROW_ID,
            strategy_id=STRATEGY_ID,
            discipline_code="consultant.structural",
            discipline_label="Structural",
            participant_type="consultant",
            request_kind="consultant_rfp",
            status="not_started",
            notes="",
            display_order=100,
            origin="derived",
            locked=locked,
            created_at=now,
            updated_at=now,
            candidates=[],
        )
    ]
    return strategy


def _patch_loaded(monkeypatch, strategy: ProcurementStrategy) -> None:
    async def loaded(_session, _project_id):
        return strategy

    monkeypatch.setattr(service, "_required_strategy", loaded)


def test_create_firm_with_files_is_one_strategy_change(monkeypatch):
    from app.procurement import candidate_submissions

    strategy = _strategy()
    _patch_loaded(monkeypatch, strategy)
    file = WorkspaceFile(id=uuid.uuid4(), project_id=PROJECT_ID, filename="quote.pdf")
    monkeypatch.setattr(candidate_submissions, "resolve_submission_files", AsyncMock(return_value=[file]))
    run_async(service.apply_procurement_strategy_operations(
        _Session(), project_id=PROJECT_ID, expected_revision=1,
        operations=[{"operation": "CREATE_CANDIDATE_FROM_FILES", "row_id": ROW_ID, "slot": 1, "company_name": "Alder Engineers", "workspace_file_ids": [str(file.id)]}],
    ))
    candidate = strategy.rows[0].candidates[0]
    assert candidate.company_name == "Alder Engineers"
    assert candidate.submission_files[0].workspace_file_id == file.id
    assert strategy.rows[0].status == "responses_received"
    assert strategy.revision == 2


def test_two_new_firms_cannot_share_a_file_in_the_same_batch(monkeypatch):
    from app.procurement import candidate_submissions

    strategy = _strategy()
    _patch_loaded(monkeypatch, strategy)
    file = WorkspaceFile(id=uuid.uuid4(), project_id=PROJECT_ID, filename="quote.pdf")
    monkeypatch.setattr(candidate_submissions, "resolve_submission_files", AsyncMock(return_value=[file]))
    with pytest.raises(service.ProcurementStrategyValidationError, match="already linked"):
        run_async(service.apply_procurement_strategy_operations(
            _Session(), project_id=PROJECT_ID, expected_revision=1,
            operations=[{"operation": "CREATE_CANDIDATE_FROM_FILES", "row_id": ROW_ID, "slot": slot, "company_name": name, "workspace_file_ids": [str(file.id)]} for slot, name in [(1, "Alder"), (2, "Birch")]],
        ))
    assert strategy.revision == 1


@pytest.mark.parametrize("condition", ["locked", "occupied", "stale", "foreign", "empty"])
def test_create_from_files_does_not_leave_a_firm_on_failure(monkeypatch, condition):
    from app.procurement import candidate_submissions

    strategy = _strategy(locked=condition == "locked")
    if condition == "occupied":
        strategy.rows[0].candidates.append(ProcurementStrategyCandidate(id=uuid.uuid4(), slot=1, company_name="Existing", submission_files=[]))
    _patch_loaded(monkeypatch, strategy)
    resolver = AsyncMock(side_effect=service.ProcurementStrategyValidationError("foreign file"))
    monkeypatch.setattr(candidate_submissions, "resolve_submission_files", resolver)
    with pytest.raises((service.ProcurementStrategyConflict, service.ProcurementStrategyValidationError)):
        run_async(service.apply_procurement_strategy_operations(
            _Session(), project_id=PROJECT_ID, expected_revision=0 if condition == "stale" else 1,
            operations=[{"operation": "CREATE_CANDIDATE_FROM_FILES", "row_id": ROW_ID, "slot": 1, "company_name": "Alder", "workspace_file_ids": [] if condition == "empty" else [str(uuid.uuid4())]}],
        ))
    assert [item.company_name for item in strategy.rows[0].candidates] == (["Existing"] if condition == "occupied" else [])
    assert strategy.revision == 1
    if condition != "foreign":
        resolver.assert_not_awaited()


def _appointment_project(
    *,
    discipline: str = "Structural",
    firm: str = "Ardent Structural",
    status: str = "Appointed",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=PROJECT_ID,
        project_metadata={
            "shared_knowledge": {
                "consultant:structural": {
                    "id": "structural",
                    "kind": "consultant",
                    "revision": 1,
                    "value": {
                        "discipline": discipline,
                        "firm": firm,
                        "status": status,
                        "fee": "$11,500.00 ex GST",
                        "evidence_paths": ["structural-fee-proposal.pdf"],
                    },
                    "source": "user",
                    "user_protected": False,
                    "updated_at": "2026-08-22T00:00:00Z",
                }
            }
        },
    )


def _structural_requirement() -> service.RequiredProjectDiscipline:
    return service.RequiredProjectDiscipline(
        code="consultant.structural",
        label="Structural",
        participant_type="consultant",
        request_kind="consultant_rfp",
        sources=("appointment",),
    )


def test_model_and_migration_define_three_column_row_record_shape() -> None:
    strategy_constraints = {
        item.name for item in ProcurementStrategy.__table__.constraints
    }
    row_indexes = {item.name for item in ProcurementStrategyRow.__table__.indexes}
    candidate_constraints = {
        item.name for item in ProcurementStrategyCandidate.__table__.constraints
    }

    assert "ck_procurement_strategies_column_count" in strategy_constraints
    assert "uq_procurement_strategy_rows_discipline" in row_indexes
    assert "uq_strategy_candidates_row_slot" in candidate_constraints
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "058_procurement_strategy.py"
    ).read_text(encoding="utf-8")
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "procurement_strategy_candidates_owner_policy" in migration


def test_ensure_attaches_rows_before_first_flush(monkeypatch) -> None:
    session = _EnsureSession()

    async def not_found(_session, _project_id):
        return None

    async def requirements(_session, *, project):
        del project
        return [_structural_requirement()]

    async def required(_session, _project_id):
        return session.strategy

    monkeypatch.setattr(service, "_load_strategy", not_found)
    monkeypatch.setattr(service, "_requirements", requirements)
    monkeypatch.setattr(service, "_required_strategy", required)

    strategy = run_async(
        service.ensure_procurement_strategy(
            session,
            project=SimpleNamespace(id=PROJECT_ID, project_metadata={}),
        )
    )

    assert strategy.rows[0].discipline_label == "Structural"
    assert session.flush_count == 1


def test_ensure_seeds_appointed_pmp_firm_and_awarded_status(monkeypatch) -> None:
    session = _EnsureSession()

    async def not_found(_session, _project_id):
        return None

    async def requirements(_session, *, project):
        del project
        return [_structural_requirement()]

    async def required(_session, _project_id):
        return session.strategy

    monkeypatch.setattr(service, "_load_strategy", not_found)
    monkeypatch.setattr(service, "_requirements", requirements)
    monkeypatch.setattr(service, "_required_strategy", required)

    strategy = run_async(
        service.ensure_procurement_strategy(
            session,
            project=_appointment_project(),
        )
    )

    assert strategy.rows[0].status == "awarded"
    assert [(item.slot, item.company_name) for item in strategy.rows[0].candidates] == [
        (1, "Ardent Structural")
    ]


def test_refresh_backfills_historical_pmp_appointment(monkeypatch) -> None:
    strategy = _strategy()
    requirement = _structural_requirement()
    strategy.source_fingerprint = service._fingerprint([requirement])
    _patch_loaded(monkeypatch, strategy)

    async def requirements(_session, *, project):
        del project
        return [requirement]

    monkeypatch.setattr(service, "_requirements", requirements)

    updated = run_async(
        service.refresh_procurement_strategy(
            _Session(),
            project=_appointment_project(),
        )
    )

    assert updated.rows[0].status == "awarded"
    assert updated.rows[0].candidates[0].company_name == "Ardent Structural"
    assert updated.revision == 2


def test_operation_adds_and_persists_tenderer_four(monkeypatch) -> None:
    strategy = _strategy()
    _patch_loaded(monkeypatch, strategy)

    updated = run_async(
        service.apply_procurement_strategy_operations(
            _Session(),
            project_id=PROJECT_ID,
            expected_revision=1,
            operations=[
                {
                    "operation": "SET_TENDERER_COLUMN_COUNT",
                    "tenderer_column_count": 4,
                }
            ],
        )
    )

    assert updated.tenderer_column_count == 4
    assert updated.revision == 2


def test_operation_rejects_stale_revision(monkeypatch) -> None:
    strategy = _strategy(revision=4)
    _patch_loaded(monkeypatch, strategy)

    with pytest.raises(service.ProcurementStrategyConflict, match="current revision is 4"):
        run_async(
            service.apply_procurement_strategy_operations(
                _Session(),
                project_id=PROJECT_ID,
                expected_revision=3,
                operations=[{"operation": "LOCK_ROW", "row_id": ROW_ID}],
            )
        )


def test_locked_row_rejects_candidate_mutation_but_can_unlock(monkeypatch) -> None:
    strategy = _strategy(locked=True)
    _patch_loaded(monkeypatch, strategy)

    with pytest.raises(service.ProcurementStrategyConflict, match="is locked"):
        run_async(
            service.apply_procurement_strategy_operations(
                _Session(),
                project_id=PROJECT_ID,
                expected_revision=1,
                operations=[
                    {
                        "operation": "UPSERT_CANDIDATE",
                        "row_id": ROW_ID,
                        "slot": 1,
                        "company_name": "North & Co",
                    }
                ],
            )
        )

    updated = run_async(
        service.apply_procurement_strategy_operations(
            _Session(),
            project_id=PROJECT_ID,
            expected_revision=1,
            operations=[{"operation": "UNLOCK_ROW", "row_id": ROW_ID}],
        )
    )
    assert updated.rows[0].locked is False


def test_consultant_appointment_marks_awarded_and_retains_firm() -> None:
    strategy = _strategy(revision=3)
    row = strategy.rows[0]

    class AppointmentSession(_Session):
        async def execute(self, _statement):
            return _ScalarResult(row)

        async def get(self, model, item_id):
            if model is ProcurementStrategy and item_id == strategy.id:
                return strategy
            return None

    changed = run_async(
        service.record_consultant_appointment(
            AppointmentSession(),
            project_id=PROJECT_ID,
            discipline="Structural Engineer",
            firm="North & Co",
        )
    )

    assert changed is True
    assert row.status == "awarded"
    assert row.candidates[0].company_name == "North & Co"
    assert row.candidates[0].slot == 1
    assert strategy.revision == 4


def test_strategy_snapshot_groups_and_sorts_rows_alphanumerically() -> None:
    strategy = _strategy()
    now = datetime(2026, 8, 22, tzinfo=UTC)

    def row(
        *,
        row_id: str,
        label: str,
        participant_type: str,
        display_order: int,
    ) -> ProcurementStrategyRow:
        return ProcurementStrategyRow(
            id=uuid.UUID(row_id),
            strategy_id=STRATEGY_ID,
            discipline_code=None,
            discipline_label=label,
            participant_type=participant_type,
            request_kind=(
                "consultant_rfp" if participant_type == "consultant" else "trade_rft"
            ),
            status="not_started",
            notes="",
            display_order=display_order,
            origin="manual",
            locked=False,
            created_at=now,
            updated_at=now,
            candidates=[],
        )

    strategy.rows = [
        row(
            row_id="00000000-0000-0000-0000-000000000010",
            label="Trade 10",
            participant_type="trade",
            display_order=100,
        ),
        row(
            row_id="00000000-0000-0000-0000-000000000020",
            label="Zulu Consultant",
            participant_type="consultant",
            display_order=200,
        ),
        row(
            row_id="00000000-0000-0000-0000-000000000002",
            label="Trade 2",
            participant_type="trade",
            display_order=300,
        ),
        row(
            row_id="00000000-0000-0000-0000-000000000001",
            label="Alpha Consultant",
            participant_type="consultant",
            display_order=400,
        ),
    ]

    class SnapshotSession(_Session):
        async def execute(self, _statement):
            return _ScalarRowsResult()

    snapshot = run_async(
        service.strategy_snapshot(SnapshotSession(), strategy=strategy)
    )

    assert [item["discipline_label"] for item in snapshot["rows"]] == [
        "Alpha Consultant",
        "Zulu Consultant",
        "Trade 2",
        "Trade 10",
    ]


@pytest.mark.parametrize("participant_type", ["consultant", "trade"])
def test_award_selects_one_firm_and_can_be_cleared(monkeypatch, participant_type):
    strategy = _strategy()
    row = strategy.rows[0]
    row.participant_type = participant_type
    first = ProcurementStrategyCandidate(id=uuid.uuid4(), slot=1, company_name="Caposi")
    second = ProcurementStrategyCandidate(id=uuid.uuid4(), slot=2, company_name="Another firm")
    row.candidates = [first, second]
    _patch_loaded(monkeypatch, strategy)
    for candidate in [first, second]:
        run_async(service.apply_procurement_strategy_operations(_Session(), project_id=PROJECT_ID, expected_revision=strategy.revision, operations=[{"operation": "AWARD_CANDIDATE", "row_id": ROW_ID, "candidate_id": candidate.id}]))
        assert row.awarded_candidate_id == candidate.id
        assert row.status == "awarded"
    run_async(service.apply_procurement_strategy_operations(_Session(), project_id=PROJECT_ID, expected_revision=strategy.revision, operations=[{"operation": "CLEAR_AWARD", "row_id": ROW_ID}]))
    assert row.awarded_candidate_id is None
    assert row.status == "not_started"


def test_award_rejects_a_firm_outside_the_row(monkeypatch):
    strategy = _strategy()
    _patch_loaded(monkeypatch, strategy)
    with pytest.raises(service.ProcurementStrategyValidationError, match="Firm not found"):
        run_async(service.apply_procurement_strategy_operations(_Session(), project_id=PROJECT_ID, expected_revision=1, operations=[{"operation": "AWARD_CANDIDATE", "row_id": ROW_ID, "candidate_id": uuid.uuid4()}]))
    assert strategy.rows[0].awarded_candidate_id is None


@pytest.mark.parametrize("operation", ["CLEAR_CANDIDATE", "UPSERT_CANDIDATE"])
def test_awarded_firm_cannot_be_silently_replaced(monkeypatch, operation):
    strategy = _strategy()
    row = strategy.rows[0]
    candidate = ProcurementStrategyCandidate(id=uuid.uuid4(), slot=1, company_name="Caposi")
    row.candidates = [candidate]
    row.awarded_candidate_id = candidate.id
    row.status = "awarded"
    _patch_loaded(monkeypatch, strategy)
    with pytest.raises(service.ProcurementStrategyConflict, match="Clear the award"):
        run_async(service.apply_procurement_strategy_operations(_Session(), project_id=PROJECT_ID, expected_revision=1, operations=[{"operation": operation, "row_id": ROW_ID, "slot": 1, "company_name": "Different firm"}]))
    assert row.awarded_candidate_id == candidate.id


def test_award_respects_locked_rows(monkeypatch):
    strategy = _strategy(locked=True)
    _patch_loaded(monkeypatch, strategy)
    with pytest.raises(service.ProcurementStrategyConflict):
        run_async(service.apply_procurement_strategy_operations(_Session(), project_id=PROJECT_ID, expected_revision=1, operations=[{"operation": "AWARD_CANDIDATE", "row_id": ROW_ID, "candidate_id": uuid.uuid4()}]))
