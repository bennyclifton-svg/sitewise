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


class _BlockingPipe:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def readline(self) -> bytes:
        return self._lines.pop(0) if self._lines else b""


class _BlockingProcess:
    def __init__(self) -> None:
        self.stdout = _BlockingPipe([b"hello\n"])
        self.stderr = _BlockingPipe([])
        self.returncode = None
        self.killed = False

    def wait(self) -> int:
        self.returncode = 0
        return 0

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
        hermes_home = Path(kwargs["env"]["HERMES_HOME"])
        seen["config"] = (hermes_home / "config.yaml").read_text(encoding="utf-8")
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
    config = seen["config"]
    assert "turn-token" not in argv
    assert "platform-key" not in argv
    assert env["AGENT_TURN_TOKEN"] == "turn-token"
    assert env["CLERK_MCP_TOKEN"] == "turn-token"
    assert env["OPENAI_API_KEY"] == "platform-key"
    assert "provider: openai-api" in config
    assert "default: gpt-5.1" in config


def test_oauth_mode_copies_existing_config_and_overlays_mcp(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.agent.hermes_process import _build_env

    source_home = tmp_path / "source-hermes"
    turn_home = tmp_path / "turn-hermes"
    source_home.mkdir()
    (source_home / "config.yaml").write_text(
        "\n".join(
            [
                "model:",
                "  default: gpt-5.5",
                "  provider: xai-oauth",
                "mcp_servers:",
                "  old:",
                '    url: "http://old.example/mcp"',
            ]
        ),
        encoding="utf-8",
    )
    (source_home / "auth.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(settings, "agent_platform_api_key", None)
    monkeypatch.setenv("HERMES_HOME", str(source_home))

    env = _build_env(
        mcp_url="http://test/mcp",
        turn_token="turn-token",
        hermes_home=turn_home,
    )

    config = (turn_home / "config.yaml").read_text(encoding="utf-8")
    assert env["HERMES_HOME"] == str(turn_home)
    assert "provider: xai-oauth" in config
    assert "old.example" not in config
    assert 'url: "http://test/mcp"' in config
    assert (turn_home / "auth.json").exists()


def test_rich_chrome_and_ansi_lines_are_stripped(tmp_path: Path) -> None:
    from app.agent.hermes_process import stream_hermes_turn

    async def spawn(**_kwargs: Any) -> _FakeProcess:
        return _FakeProcess(
            stdout=[
                "Query: hello\n",
                "wrapped query echo\n",
                "Initializing agent...\n",
                "\x1b[31m\u256d\u2500 Hermes \u2500\u256e\x1b[0m\n",
                "\u250a \u26a1 mcp_clerk   1.3s\n",
                "  Useful answer\n",
                "\u2570\u2500\u2500\u2500\u2500\u256f\n",
                "Resume this session with:\n",
                "hermes --resume 20260703_abc\n",
                "Duration:       4s\n",
                "Messages:       4 (1 user, 2 tool calls)\n",
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


def test_default_spawn_falls_back_when_async_subprocess_is_unavailable(monkeypatch) -> None:
    from app.agent.hermes_process import _default_spawn

    process = _BlockingProcess()

    async def unavailable_subprocess(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr("asyncio.create_subprocess_exec", unavailable_subprocess)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: process)

    async def _run() -> None:
        spawned = await _default_spawn(argv=["hermes"], env={}, cwd=".")
        assert spawned.stdout is not None
        assert await spawned.stdout.readline() == b"hello\n"
        assert await spawned.wait() == 0

    run_async(_run())
