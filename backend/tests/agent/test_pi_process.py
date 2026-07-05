import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.agent.pi_process import (
    PiTurnError,
    _prompt_file_arg,
    _write_prompt_file,
    resolve_subprocess_binary,
    stream_pi_turn,
    text_delta_from_pi_event,
)
from tests.conftest import run_async


class _FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = [line.encode() for line in lines]

    async def readline(self) -> bytes:
        await asyncio.sleep(0)
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout: list[str],
        stderr: list[str] | None = None,
        returncode: int = 0,
    ) -> None:
        self.stdout = _FakeStream(stdout)
        self.stderr = _FakeStream(stderr or [])
        self.returncode = returncode
        self.killed = False

    async def wait(self) -> int:
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def _collect(iterator) -> list[str]:
    async def _run() -> list[str]:
        return [chunk async for chunk in iterator]

    return run_async(_run())


def test_text_delta_from_pi_event_returns_assistant_text_delta() -> None:
    line = (
        '{"type":"message_update","assistantMessageEvent":'
        '{"type":"text_delta","delta":"hello"}}'
    )
    assert text_delta_from_pi_event(line) == "hello"


def test_text_delta_from_pi_event_ignores_non_text_events() -> None:
    line = '{"type":"tool_execution_start","toolName":"clerk_search_documents"}'
    assert text_delta_from_pi_event(line) is None


def test_resolve_subprocess_binary_uses_shutil_which(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.shutil.which",
        lambda name: "C:\\npm\\pi.cmd" if name == "pi" else None,
    )
    assert resolve_subprocess_binary("pi") == "C:\\npm\\pi.cmd"


def test_prompt_file_arg_points_to_full_multiline_prompt(tmp_path: Path) -> None:
    prompt = (
        "<persona>\n"
        "You are Clerk.\n"
        "</persona>\n\n"
        "<project-context>\n"
        "project_title: Walsh Reno\n"
        "subclasses: House (Class 1a)\n"
        "</project-context>"
    )

    prompt_path = _write_prompt_file(tmp_path, prompt=prompt)

    try:
        prompt_arg = _prompt_file_arg(tmp_path, prompt_path)

        assert prompt_path.read_text(encoding="utf-8") == prompt
        assert prompt_arg.startswith("@.pi/turn-prompts/")
        assert prompt_arg.endswith(".md")
        assert "\n" not in prompt_arg
    finally:
        prompt_path.unlink(missing_ok=True)


def test_stream_pi_turn_passes_prompt_as_at_file_and_cleans_up(tmp_path: Path) -> None:
    prompt = (
        "<persona>\n"
        "You are Clerk.\n"
        "</persona>\n\n"
        "<project-context>\n"
        "project_title: Walsh Reno\n"
        "building_class: residential\n"
        "work_type: refurb\n"
        "subclasses: House (Class 1a)\n"
        "scale: GFA sqm=200\n"
        "</project-context>\n\n"
        "what can you tell me about the project"
    )
    seen: dict[str, Any] = {}

    async def spawn(**kwargs: Any) -> _FakeProcess:
        seen.update(kwargs)
        prompt_arg = kwargs["argv"][-1]
        prompt_path = Path(kwargs["cwd"]) / prompt_arg.removeprefix("@")
        seen["prompt_arg"] = prompt_arg
        seen["prompt_path"] = prompt_path
        seen["prompt_text"] = prompt_path.read_text(encoding="utf-8")
        return _FakeProcess(
            stdout=[
                '{"type":"message_update","assistantMessageEvent":'
                '{"type":"text_delta","delta":"ok"}}\n'
            ]
        )

    chunks = _collect(
        stream_pi_turn(
            prompt=prompt,
            mcp_url="http://test/mcp",
            turn_token="turn-token",
            cwd=tmp_path,
            spawn=spawn,
        )
    )

    assert chunks == ["ok"]
    assert seen["argv"][-2:] == ["-p", seen["prompt_arg"]]
    assert seen["prompt_arg"].startswith("@.pi/turn-prompts/")
    assert prompt not in seen["argv"]
    assert all("\n" not in part for part in seen["argv"])
    assert seen["prompt_text"] == prompt
    assert not seen["prompt_path"].exists()


def test_stream_pi_turn_cleans_prompt_file_when_spawn_fails(tmp_path: Path) -> None:
    seen: dict[str, Path] = {}

    async def spawn(**kwargs: Any) -> _FakeProcess:
        prompt_arg = kwargs["argv"][-1]
        seen["prompt_path"] = Path(kwargs["cwd"]) / prompt_arg.removeprefix("@")
        raise FileNotFoundError

    with pytest.raises(PiTurnError):
        _collect(
            stream_pi_turn(
                prompt="project_title: Walsh Reno",
                mcp_url="http://test/mcp",
                turn_token="turn-token",
                cwd=tmp_path,
                spawn=spawn,
            )
        )

    assert not seen["prompt_path"].exists()
