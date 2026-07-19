from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.agent.process_tree import subprocess_group_options, terminate_process_tree

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_RICH_BORDER_CHARS = (
    "\u2500\u2502\u250a\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c"
    "\u2550\u2551\u256d\u256e\u256f\u2570"
)
_SKIP_PREFIXES = (
    "Query:",
    "Initializing agent",
    "Session:",
    "Resume this session with:",
    "hermes --resume",
    "Duration:",
    "Messages:",
    "Goodbye!",
    "Warning: Unknown toolsets:",
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


class _ThreadedStream:
    def __init__(self, stream) -> None:
        self._stream = stream

    async def readline(self) -> bytes:
        return await asyncio.to_thread(self._stream.readline)


class _ThreadedProcess:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process
        self.stdout = _ThreadedStream(process.stdout) if process.stdout is not None else None
        self.stderr = _ThreadedStream(process.stderr) if process.stderr is not None else None

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        return self._process.returncode

    async def wait(self) -> int:
        return await asyncio.to_thread(self._process.wait)

    def kill(self) -> None:
        self._process.kill()

    def send_signal(self, sig: int) -> None:
        self._process.send_signal(sig)


def _spawn_threaded_process(
    *,
    argv: list[str],
    env: dict[str, str],
    cwd: str,
) -> _ThreadedProcess:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **subprocess_group_options(),
    )
    return _ThreadedProcess(process)


async def _default_spawn(*, argv: list[str], env: dict[str, str], cwd: str) -> _Process:
    try:
        return await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **subprocess_group_options(),
        )
    except NotImplementedError:
        return await asyncio.to_thread(
            _spawn_threaded_process,
            argv=argv,
            env=env,
            cwd=cwd,
        )


def _build_argv(
    prompt: str,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> list[str]:
    if settings.hermes_invocation_mode == "oneshot":
        argv = [settings.hermes_binary_path, "-z", prompt]
        if provider:
            argv.extend(["--provider", provider])
        if model:
            argv.extend(["--model", model])
        return argv

    argv = [
        settings.hermes_binary_path,
        "chat",
        "-q",
        prompt,
        "--source",
        "tool",
    ]
    if provider:
        argv.extend(["--provider", provider])
    if model:
        argv.extend(["--model", model])
    return argv


def _existing_hermes_home(env: dict[str, str]) -> Path | None:
    candidates: list[Path] = []
    if env.get("HERMES_HOME"):
        candidates.append(Path(env["HERMES_HOME"]))
    if env.get("LOCALAPPDATA"):
        candidates.append(Path(env["LOCALAPPDATA"]) / "hermes")
    candidates.append(Path.home() / ".hermes")

    for candidate in candidates:
        if (candidate / "config.yaml").exists():
            return candidate
    return None


def _copy_hermes_credentials(source_home: Path, hermes_home: Path) -> None:
    for filename in ("auth.json", ".env"):
        source = source_home / filename
        if source.exists():
            shutil.copy2(source, hermes_home / filename)


def _strip_top_level_yaml_block(text: str, key: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    marker = f"{key}:"

    for line in lines:
        if line == marker:
            skipping = True
            continue
        if skipping and line and not line.startswith((" ", "\t")):
            skipping = False
        if not skipping:
            kept.append(line)

    return "\n".join(kept).rstrip()


def _mcp_config_block(*, mcp_url: str) -> str:
    return "\n".join(
        [
            "mcp_servers:",
            "  clerk:",
            f'    url: "{mcp_url}"',
            "    headers:",
            '      Authorization: "Bearer ${CLERK_MCP_TOKEN}"',
            "",
        ]
    )


def _write_platform_key_config(hermes_home: Path, *, mcp_url: str) -> None:
    config = "\n".join(
        [
            "model:",
            f"  provider: {settings.hermes_model_provider}",
            f"  default: {settings.hermes_model}",
            _mcp_config_block(mcp_url=mcp_url),
        ]
    )
    (hermes_home / "config.yaml").write_text(config, encoding="utf-8")


def _write_hermes_config(
    hermes_home: Path,
    *,
    mcp_url: str,
    source_home: Path | None,
) -> None:
    hermes_home.mkdir(parents=True, exist_ok=True)

    if settings.agent_platform_api_key or source_home is None:
        _write_platform_key_config(hermes_home, mcp_url=mcp_url)
        return

    source_config = (source_home / "config.yaml").read_text(encoding="utf-8")
    base_config = _strip_top_level_yaml_block(source_config, "mcp_servers")
    config = f"{base_config}\n{_mcp_config_block(mcp_url=mcp_url)}"
    (hermes_home / "config.yaml").write_text(config, encoding="utf-8")
    _copy_hermes_credentials(source_home, hermes_home)


def _build_env(
    *,
    mcp_url: str,
    turn_token: str,
    hermes_home: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    source_home = _existing_hermes_home(env)
    env["HERMES_HOME"] = str(hermes_home)
    env["AGENT_TURN_TOKEN"] = turn_token
    env["CLERK_MCP_TOKEN"] = turn_token
    if settings.agent_platform_api_key:
        env["OPENAI_API_KEY"] = settings.agent_platform_api_key
    _write_hermes_config(hermes_home, mcp_url=mcp_url, source_home=source_home)
    return env


def clean_hermes_output_line(line: str) -> str | None:
    cleaned = _ANSI_RE.sub("", line).strip()
    if not cleaned:
        return None
    if cleaned.startswith(_SKIP_PREFIXES):
        return None
    if "mcp_" in cleaned and "\u26a1" in cleaned:
        return None
    if any(ch in _RICH_BORDER_CHARS for ch in cleaned):
        without_borders = "".join(
            ch for ch in cleaned if ch not in _RICH_BORDER_CHARS
        ).strip()
        normalized = without_borders.replace("\u2695", "").strip()
        if not without_borders or normalized == "Hermes":
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
    skipping_query_echo = False
    while True:
        raw = await stream.readline()
        if not raw:
            return
        line = raw.decode(errors="replace")
        cleaned = _ANSI_RE.sub("", line).strip()
        if cleaned.startswith("Query:"):
            skipping_query_echo = True
            continue
        if skipping_query_echo:
            if cleaned.startswith("Initializing agent"):
                skipping_query_echo = False
            continue
        text = clean_hermes_output_line(line)
        if text:
            yield text


def _stderr_tail_text(stderr_tail: deque[str]) -> str:
    return "\n".join(stderr_tail).strip()


async def _kill_and_wait(process: _Process) -> None:
    await terminate_process_tree(process)


async def stream_hermes_turn(
    *,
    prompt: str,
    mcp_url: str,
    turn_token: str,
    cwd: str | Path,
    provider: str | None = None,
    model: str | None = None,
    spawn: Spawn = _default_spawn,
) -> AsyncIterator[str]:
    argv = _build_argv(prompt, provider=provider, model=model)
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
                if process.returncode is not None:
                    await asyncio.gather(stderr_task, return_exceptions=True)

            if returncode != 0:
                tail = _stderr_tail_text(stderr_tail)
                message = f"Hermes exited with code {returncode}"
                if tail:
                    message = f"{message}: {tail}"
                raise HermesTurnError(message)
        except BaseException:
            if process.returncode is None:
                await _kill_and_wait(process)
            if not stderr_task.done():
                stderr_task.cancel()
            await asyncio.gather(stderr_task, return_exceptions=True)
            raise
        finally:
            if isinstance(getattr(process, "pid", None), int):
                await _kill_and_wait(process)
