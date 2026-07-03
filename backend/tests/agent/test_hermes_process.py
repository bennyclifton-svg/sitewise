import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.config import settings
from tests.conftest import run_async


class _FakeStream:
    def __init__(self, lines: list[str], *, delay: float = 0) -> None:
        self._lines = [line.encode() for line in lines]
        self._delay = delay

    async def readline(self) -> bytes:
        if self._delay:
            await asyncio.sleep(self._delay)
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
        delay: float = 0,
    ) -> None:
        self.stdout = _FakeStream(stdout, delay=delay)
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


def test_stream_hermes_turn_yields_clean_chunks_in_order(tmp_path: Path) -> None:
    from app.agent.hermes_process import stream_hermes_turn

    async def spawn(**_kwargs: Any) -> _FakeProcess:
        return _FakeProcess(stdout=["Hello\n", " world\n"])

    chunks = _collect(
        stream_hermes_turn(
            prompt="Say hello",
            mcp_url="http://test/mcp",
            turn_token="secret-token",
            cwd=tmp_path,
            spawn=spawn,
        )
    )

    assert chunks == ["Hello", "world"]


def test_secrets_are_in_env_not_argv(monkeypatch, tmp_path: Path) -> None:
    from app.agent.hermes_process import stream_hermes_turn

    seen: dict[str, Any] = {}
    monkeypatch.setattr(settings, "agent_platform_api_key", "platform-key")

    async def spawn(**kwargs: Any) -> _FakeProcess:
        seen.update(kwargs)
        return _FakeProcess(stdout=["ok\n"])

    _collect(
        stream_hermes_turn(
            prompt="Use tools",
            mcp_url="http://test/mcp",
            turn_token="turn-token",
            cwd=tmp_path,
            spawn=spawn,
        )
    )

    argv = " ".join(seen["argv"])
    env = seen["env"]
    assert "turn-token" not in argv
    assert "platform-key" not in argv
    assert env["AGENT_TURN_TOKEN"] == "turn-token"
    assert env["CLERK_MCP_TOKEN"] == "turn-token"
    assert env["OPENAI_API_KEY"] == "platform-key"


def test_rich_chrome_and_ansi_lines_are_stripped(tmp_path: Path) -> None:
    from app.agent.hermes_process import stream_hermes_turn

    async def spawn(**_kwargs: Any) -> _FakeProcess:
        return _FakeProcess(
            stdout=[
                "Query: hello\n",
                "Initializing agent...\n",
                "\x1b[31m\u256d\u2500 Hermes \u2500\u256e\x1b[0m\n",
                "  Useful answer\n",
                "\u2570\u2500\u2500\u2500\u2500\u256f\n",
                "Session: 20260703_abc\n",
            ]
        )

    chunks = _collect(
        stream_hermes_turn(
            prompt="hello",
            mcp_url="http://test/mcp",
            turn_token="token",
            cwd=tmp_path,
            spawn=spawn,
        )
    )

    assert chunks == ["Useful answer"]


def test_non_zero_exit_raises_with_stderr_tail(tmp_path: Path) -> None:
    from app.agent.hermes_process import HermesTurnError, stream_hermes_turn

    async def spawn(**_kwargs: Any) -> _FakeProcess:
        return _FakeProcess(
            stdout=[],
            stderr=["first\n", "important failure\n"],
            returncode=7,
        )

    with pytest.raises(HermesTurnError, match="important failure"):
        _collect(
            stream_hermes_turn(
                prompt="fail",
                mcp_url="http://test/mcp",
                turn_token="token",
                cwd=tmp_path,
                spawn=spawn,
            )
        )


def test_timeout_kills_child(monkeypatch, tmp_path: Path) -> None:
    from app.agent.hermes_process import HermesTurnTimeout, stream_hermes_turn

    process = _FakeProcess(stdout=["late\n"], delay=0.05)
    monkeypatch.setattr(settings, "agent_turn_timeout_seconds", 0.01)

    async def spawn(**_kwargs: Any) -> _FakeProcess:
        return process

    with pytest.raises(HermesTurnTimeout):
        _collect(
            stream_hermes_turn(
                prompt="slow",
                mcp_url="http://test/mcp",
                turn_token="token",
                cwd=tmp_path,
                spawn=spawn,
            )
        )

    assert process.killed
