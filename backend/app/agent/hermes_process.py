from __future__ import annotations

import asyncio
import os
import re
import tempfile
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Protocol

from app.config import settings

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_RICH_BORDER_CHARS = (
    "\u2500\u2502\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
    "\u2550\u2551\u256d\u256e\u256f\u2570"
)
_SKIP_PREFIXES = (
    "Query:",
    "Initializing agent",
    "Session:",
)


class HermesTurnError(Exception):
    pass


class HermesTurnTimeout(HermesTurnError):
    pass


class _Stream(Protocol):
    async def readline(self) -> bytes:
        ...


class _Process(Protocol):
    stdout: _Stream | None
    stderr: _Stream | None
    returncode: int | None

    async def wait(self) -> int:
        ...

    def kill(self) -> None:
        ...


Spawn = Callable[..., Awaitable[_Process]]


async def _default_spawn(*, argv: list[str], env: dict[str, str], cwd: str) -> _Process:
    return await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


def _build_argv(prompt: str) -> list[str]:
    if settings.hermes_invocation_mode == "oneshot":
        return [settings.hermes_binary_path, "-z", prompt]
    return [
        settings.hermes_binary_path,
        "chat",
        "-q",
        prompt,
        "--source",
        "tool",
    ]


def _write_hermes_config(hermes_home: Path, *, mcp_url: str) -> None:
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / "config.yaml").write_text(
        "\n".join(
            [
                "model:",
                "  provider: openai",
                f"  default: {settings.openai_chat_model}",
                "mcp_servers:",
                "  clerk:",
                f'    url: "{mcp_url}"',
                "    headers:",
                '      Authorization: "Bearer ${CLERK_MCP_TOKEN}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _build_env(
    *,
    mcp_url: str,
    turn_token: str,
    hermes_home: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["AGENT_TURN_TOKEN"] = turn_token
    env["CLERK_MCP_TOKEN"] = turn_token
    if settings.agent_platform_api_key:
        env["OPENAI_API_KEY"] = settings.agent_platform_api_key
    _write_hermes_config(hermes_home, mcp_url=mcp_url)
    return env


def clean_hermes_output_line(line: str) -> str | None:
    cleaned = _ANSI_RE.sub("", line).strip()
    if not cleaned:
        return None
    if cleaned.startswith(_SKIP_PREFIXES):
        return None
    if any(ch in _RICH_BORDER_CHARS for ch in cleaned):
        without_borders = "".join(
            ch for ch in cleaned if ch not in _RICH_BORDER_CHARS
        ).strip()
        if not without_borders or without_borders == "Hermes":
            return None
    return cleaned


async def _read_stderr(stream: _Stream | None, tail: deque[str]) -> None:
    if stream is None:
        return
    while True:
        raw = await stream.readline()
        if not raw:
            return
        tail.append(raw.decode(errors="replace").rstrip())


async def _iter_stdout(stream: _Stream | None) -> AsyncIterator[str]:
    if stream is None:
        return
    while True:
        raw = await stream.readline()
        if not raw:
            return
        text = clean_hermes_output_line(raw.decode(errors="replace"))
        if text:
            yield text


def _stderr_tail_text(stderr_tail: deque[str]) -> str:
    return "\n".join(stderr_tail).strip()


async def _kill_and_wait(process: _Process) -> None:
    process.kill()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except Exception:
        pass


async def stream_hermes_turn(
    *,
    prompt: str,
    mcp_url: str,
    turn_token: str,
    cwd: str | Path,
    spawn: Spawn = _default_spawn,
) -> AsyncIterator[str]:
    argv = _build_argv(prompt)
    stderr_tail: deque[str] = deque(maxlen=20)

    with tempfile.TemporaryDirectory(prefix="clerk-hermes-") as hermes_home:
        env = _build_env(
            mcp_url=mcp_url,
            turn_token=turn_token,
            hermes_home=Path(hermes_home),
        )
        process = await spawn(argv=argv, env=env, cwd=str(cwd))
        stderr_task = asyncio.create_task(_read_stderr(process.stderr, stderr_tail))
        try:
            try:
                async with asyncio.timeout(settings.agent_turn_timeout_seconds):
                    async for chunk in _iter_stdout(process.stdout):
                        yield chunk
                    returncode = await process.wait()
            except TimeoutError as exc:
                await _kill_and_wait(process)
                raise HermesTurnTimeout("Hermes turn timed out") from exc
            finally:
                await asyncio.gather(stderr_task, return_exceptions=True)

            if returncode != 0:
                tail = _stderr_tail_text(stderr_tail)
                message = f"Hermes exited with code {returncode}"
                if tail:
                    message = f"{message}: {tail}"
                raise HermesTurnError(message)
        except Exception:
            if not stderr_task.done():
                stderr_task.cancel()
            raise
