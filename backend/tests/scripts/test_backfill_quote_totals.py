import asyncio
import uuid
from types import SimpleNamespace

from scripts import backfill_quote_totals as backfill_module


def run_async(coro):
    return asyncio.run(coro)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.commit_count = 0

    async def execute(self, _statement):
        return _Result(self.rows)

    async def commit(self):
        self.commit_count += 1


def _quote():
    return SimpleNamespace(
        id=uuid.uuid4(),
        stated_total_cents=None,
        stated_total_source=None,
    )


def test_backfill_is_dry_run_by_default(monkeypatch) -> None:
    quote = _quote()
    session = _Session([(quote, uuid.uuid4())])

    async def cached_total(*_args, **_kwargs):
        return 125_000

    monkeypatch.setattr(backfill_module, "_cached_total", cached_total)

    summary = run_async(
        backfill_module.backfill_quote_totals(session, apply=False)
    )

    assert summary.quotes_missing_total == 1
    assert summary.backfilled == 1
    assert summary.applied is False
    assert quote.stated_total_cents is None
    assert quote.stated_total_source is None
    assert session.commit_count == 0


def test_backfill_applies_cached_total_and_reports_misses(monkeypatch) -> None:
    matched = _quote()
    missing = _quote()
    session = _Session(
        [(matched, uuid.uuid4()), (missing, uuid.uuid4())]
    )

    async def cached_total(_session, *, quote_id, project_id):
        del _session, project_id
        return 125_000 if quote_id == matched.id else None

    monkeypatch.setattr(backfill_module, "_cached_total", cached_total)

    summary = run_async(backfill_module.backfill_quote_totals(session, apply=True))

    assert summary.quotes_missing_total == 2
    assert summary.backfilled == 1
    assert summary.no_cached_total == [str(missing.id)]
    assert summary.applied is True
    assert matched.stated_total_cents == 125_000
    assert matched.stated_total_source == "extracted"
    assert session.commit_count == 1
