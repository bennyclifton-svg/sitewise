import asyncio
import uuid

import pytest

from app.agent.turn_supervisor import TurnSupervisor
from tests.conftest import run_async


class MemoryJournal:
    def __init__(self):
        self.events = {}
        self.repaired = []

    async def append(self, turn_id, events):
        self.events.setdefault(turn_id, []).extend(events)

    async def read(self, turn_id, after=0):
        rows = self.events.get(turn_id, [])
        return list(enumerate(rows[after:], start=after + 1)), bool(
            rows and rows[-1] == "data: [DONE]\n\n"
        )

    async def repair(self, turn_id):
        if self.events.get(turn_id, [])[-1:] == ["data: [DONE]\n\n"]:
            return
        self.repaired.append(turn_id)
        await self.append(
            turn_id,
            [
                'data: {"type":"error","errorText":"Interrupted"}\n\n',
                "data: [DONE]\n\n",
            ],
        )


@pytest.mark.parametrize("phase", ["read", "search", "write"])
def test_disconnect_does_not_cancel_execution_and_replay_does_not_repeat_mutation(
    phase,
):
    async def run():
        journal = MemoryJournal()
        supervisor = TurnSupervisor(journal, flush_seconds=0.001)
        turn_id = uuid.uuid4()
        reached, release = asyncio.Event(), asyncio.Event()
        writes = []

        async def source():
            yield f'data: {{"phase":"{phase}"}}\n\n'
            if phase == "write":
                writes.append("committed")
            reached.set()
            await release.wait()
            if phase != "write":
                writes.append("committed")
            yield "data: [DONE]\n\n"

        supervisor.start(turn_id, source())
        await reached.wait()
        stream = supervisor.stream(turn_id)
        first = await anext(stream)
        assert "id: 1" in first
        await stream.aclose()
        assert supervisor.running(turn_id)
        release.set()
        replay = [event async for event in supervisor.stream(turn_id, after=1)]
        assert any("[DONE]" in event for event in replay)
        assert writes == ["committed"]
        assert len(journal.events[turn_id]) == 2
        await supervisor.close()

    run_async(run())


def test_explicit_cancel_stops_source_and_preserves_committed_work():
    async def run():
        journal = MemoryJournal()
        supervisor = TurnSupervisor(journal, flush_seconds=0.001)
        turn_id = uuid.uuid4()
        started, stopped = asyncio.Event(), asyncio.Event()

        async def source():
            try:
                started.set()
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                stopped.set()

        supervisor.start(turn_id, source())
        await started.wait()
        assert supervisor.cancel(turn_id)
        await supervisor.close()
        assert stopped.is_set()
        assert journal.repaired == [turn_id]

    run_async(run())


def test_journal_failure_cancels_execution_instead_of_running_unobserved():
    async def run():
        class FailedJournal(MemoryJournal):
            async def append(self, turn_id, events):
                raise OSError("private database connection")

            async def repair(self, turn_id):
                self.repaired.append(turn_id)

        journal = FailedJournal()
        supervisor = TurnSupervisor(journal, flush_seconds=0.001)
        stopped = asyncio.Event()

        async def source():
            try:
                yield 'data: {"type":"start"}\n\n'
                await asyncio.Event().wait()
            finally:
                stopped.set()

        supervisor.start(uuid.uuid4(), source())
        await asyncio.wait_for(stopped.wait(), timeout=1)
        await supervisor.close()
        assert len(journal.repaired) == 1

    run_async(run())
