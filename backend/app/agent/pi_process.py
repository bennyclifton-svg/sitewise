"""Pi agent subprocess for corpus Q&A turns (retrieval MCP tools only)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Protocol

from app.config import settings

PI_MCP_DIRECT_TOOLS = (
    "list_project_files",
    "read_project_workbook",
    "read_workspace_file",
    "forecast_consultant_fees",
    "apply_consultant_fee_forecast",
    "draft_consultant_procurement_artifact",
    "find_document_text",
    "search_documents",
    "get_document",
    "list_platform_knowledge",
    "search_platform_knowledge",
    "read_platform_knowledge",
)


class PiTurnError(Exception):
    pass


class PiTurnTimeout(PiTurnError):
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
    def returncode(self) -> int | None:
        return self._process.returncode

    async def wait(self) -> int:
        return await asyncio.to_thread(self._process.wait)

    def kill(self) -> None:
        self._process.kill()


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
        )
    except NotImplementedError:
        return await asyncio.to_thread(
            _spawn_threaded_process,
            argv=argv,
            env=env,
            cwd=cwd,
        )


def resolve_subprocess_binary(binary: str) -> str:
    """Resolve a command to an executable path (npm .cmd shims on Windows need this)."""
    path = Path(binary)
    if path.is_file():
        return str(path.resolve())
    resolved = shutil.which(binary)
    if resolved:
        return resolved
    return binary


def _build_argv(*, prompt_arg: str) -> list[str]:
    return [
        resolve_subprocess_binary(settings.pi_binary_path),
        "--no-tools",
        "--provider",
        settings.pi_model_provider,
        "--model",
        settings.pi_model,
        "--thinking",
        "off",
        "--no-session",
        "--mode",
        "json",
        "-p",
        prompt_arg,
    ]


def _write_pi_mcp_config(cwd: Path, *, mcp_url: str) -> None:
    pi_dir = cwd / ".pi"
    pi_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "mcpServers": {
            "clerk": {
                "url": mcp_url,
                "headers": {"Authorization": "Bearer ${CLERK_MCP_TOKEN}"},
                "bearerTokenEnv": "CLERK_MCP_TOKEN",
                "directTools": list(PI_MCP_DIRECT_TOOLS),
            }
        }
    }
    (pi_dir / "mcp.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_prompt_file(workspace: Path, *, prompt: str) -> Path:
    prompt_dir = workspace / ".pi" / "turn-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{uuid.uuid4().hex}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _prompt_file_arg(workspace: Path, prompt_path: Path) -> str:
    relative = prompt_path.relative_to(workspace)
    return f"@{relative.as_posix()}"


def _build_env(*, mcp_url: str, turn_token: str, cwd: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CLERK_MCP_TOKEN"] = turn_token
    env["AGENT_TURN_TOKEN"] = turn_token
    env["PI_OFFLINE"] = "1"
    if settings.agent_platform_api_key:
        env["OPENAI_API_KEY"] = settings.agent_platform_api_key
    _write_pi_mcp_config(cwd, mcp_url=mcp_url)
    return env


def text_delta_from_pi_event(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line.startswith("{"):
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if event.get("type") != "message_update":
        return None
    assistant_event = event.get("assistantMessageEvent") or {}
    if assistant_event.get("type") != "text_delta":
        return None
    delta = assistant_event.get("delta")
    return delta if isinstance(delta, str) and delta else None


async def _read_stderr(stream: _Stream | None, tail: deque[str]) -> None:
    if stream is None:
        return
    while True:
        raw = await stream.readline()
        if not raw:
            return
        tail.append(raw.decode(errors="replace").rstrip())


async def _iter_pi_stdout(stream: _Stream | None) -> AsyncIterator[str]:
    if stream is None:
        return
    while True:
        raw = await stream.readline()
        if not raw:
            return
        line = raw.decode(errors="replace")
        delta = text_delta_from_pi_event(line)
        if delta:
            yield delta


async def _kill_and_wait(process: _Process) -> None:
    process.kill()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except Exception:
        pass


async def stream_pi_turn(
    *,
    prompt: str,
    mcp_url: str,
    turn_token: str,
    cwd: str | Path,
    spawn: Spawn = _default_spawn,
) -> AsyncIterator[str]:
    workspace = Path(cwd)
    workspace.mkdir(parents=True, exist_ok=True)
    prompt_path: Path | None = None

    try:
        prompt_path = _write_prompt_file(workspace, prompt=prompt)
        argv = _build_argv(prompt_arg=_prompt_file_arg(workspace, prompt_path))
        env = _build_env(mcp_url=mcp_url, turn_token=turn_token, cwd=workspace)
        stderr_tail: deque[str] = deque(maxlen=20)

        try:
            process = await spawn(argv=argv, env=env, cwd=str(workspace))
        except FileNotFoundError as exc:
            binary = argv[0]
            raise PiTurnError(
                f"Cannot run Pi agent binary '{binary}'. "
                "On Windows, npm-installed `pi` is a .cmd shim - set PI_BINARY_PATH "
                "to the full path (for example "
                "C:\\Users\\<you>\\AppData\\Roaming\\npm\\pi.cmd), or install pi "
                "where Python can execute it directly."
            ) from exc

        stderr_task = asyncio.create_task(_read_stderr(process.stderr, stderr_tail))
        try:
            try:
                async with asyncio.timeout(settings.agent_turn_timeout_seconds):
                    async for chunk in _iter_pi_stdout(process.stdout):
                        yield chunk
                    returncode = await process.wait()
            except TimeoutError as exc:
                await _kill_and_wait(process)
                raise PiTurnTimeout("Pi turn timed out") from exc
            finally:
                await asyncio.gather(stderr_task, return_exceptions=True)

            if returncode != 0:
                tail = "\n".join(stderr_tail).strip()
                message = f"Pi exited with code {returncode}"
                if tail:
                    message = f"{message}: {tail}"
                raise PiTurnError(message)
        except Exception:
            if not stderr_task.done():
                stderr_task.cancel()
            raise
    finally:
        if prompt_path is not None:
            prompt_path.unlink(missing_ok=True)
