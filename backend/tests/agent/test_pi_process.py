import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.agent.pi_process import (
    PiTurnError,
    _default_spawn,
    _build_argv,
    _iter_pi_stdout,
    pi_builtin_tools_flag,
    _prompt_file_arg,
    _write_pi_mcp_config,
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


def test_default_spawn_reads_large_terminal_event_after_text_delta(
    monkeypatch, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}

    async def fake_create_subprocess_exec(*argv: str, **kwargs: Any):
        seen["limit"] = kwargs.get("limit")
        reader = asyncio.StreamReader(limit=kwargs.get("limit", 2**16))
        text_delta = json.dumps(
            {
                "type": "message_update",
                "assistantMessageEvent": {
                    "type": "text_delta",
                    "delta": "final answer",
                },
            }
        ).encode()
        terminal_event = json.dumps(
            {
                "type": "agent_end",
                "messages": [{"role": "toolResult", "content": "x" * (2**16)}],
            }
        ).encode()
        reader.feed_data(text_delta + b"\n" + terminal_event + b"\n")
        reader.feed_eof()

        class FakeProcess:
            stdout = reader
            stderr = None

        return FakeProcess()

    monkeypatch.setattr(
        "app.agent.pi_process.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    async def run_replay() -> list[str]:
        process = await _default_spawn(argv=["pi"], env={}, cwd=str(tmp_path))
        return [chunk async for chunk in _iter_pi_stdout(process.stdout)]

    assert run_async(run_replay()) == ["final answer"]
    assert seen["limit"] == 16 * 1024 * 1024


def test_resolve_subprocess_binary_uses_shutil_which(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.shutil.which",
        lambda name: "C:\\npm\\pi.cmd" if name == "pi" else None,
    )
    assert resolve_subprocess_binary("pi") == "C:\\npm\\pi.cmd"


def test_prompt_file_arg_points_to_full_multiline_prompt(tmp_path: Path) -> None:
    prompt = (
        "<persona>\n"
        "You are Pi.\n"
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


def test_pi_mcp_config_allows_the_tender_comparison_workflow(tmp_path: Path) -> None:
    _write_pi_mcp_config(tmp_path, mcp_url="http://test/mcp")

    config = json.loads((tmp_path / ".pi" / "mcp.json").read_text(encoding="utf-8"))
    direct_tools = config["mcpServers"]["clerk"]["directTools"]

    assert {
        "list_tender_comparisons",
        "get_tender_comparison",
        "get_comparison_status",
        "get_comparison_result",
        "start_tender_comparison",
        "prepare_tender_comparison",
        "find_candidate_tender_documents",
        "get_tender_quote_selection",
        "replace_tender_quote_selection",
    } <= set(direct_tools)


def test_pi_mcp_config_only_allows_web_tools_when_enabled(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.settings.agent_web_research_enabled",
        False,
    )
    _write_pi_mcp_config(tmp_path, mcp_url="http://test/mcp")
    disabled_config = json.loads(
        (tmp_path / ".pi" / "mcp.json").read_text(encoding="utf-8")
    )

    monkeypatch.setattr(
        "app.agent.pi_process.settings.agent_web_research_enabled",
        True,
    )
    _write_pi_mcp_config(tmp_path, mcp_url="http://test/mcp")
    enabled_config = json.loads(
        (tmp_path / ".pi" / "mcp.json").read_text(encoding="utf-8")
    )

    disabled = set(disabled_config["mcpServers"]["clerk"]["directTools"])
    enabled = set(enabled_config["mcpServers"]["clerk"]["directTools"])
    assert {"search_web", "read_web_source"}.isdisjoint(disabled)
    assert {"search_web", "read_web_source"} <= enabled


def test_pi_builtin_tools_flag_uses_the_legacy_flag_when_needed(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="--no-tools Disable all built-in tools\n",
            stderr="",
        ),
    )

    assert pi_builtin_tools_flag("pi") == "--no-tools"


def test_stream_pi_turn_passes_prompt_as_at_file_and_cleans_up(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.pi_builtin_tools_flag",
        lambda _binary: "--no-builtin-tools",
    )
    prompt = (
        "<persona>\n"
        "You are Pi.\n"
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
            provider="openai",
            model="gpt-5.6-sol",
            spawn=spawn,
        )
    )

    assert chunks == ["ok"]
    assert "--no-builtin-tools" in seen["argv"]
    assert "--no-tools" not in seen["argv"]
    assert {"--no-skills", "--no-prompt-templates", "--no-themes"} <= set(seen["argv"])
    assert seen["argv"][seen["argv"].index("--provider") + 1] == "openai"
    assert seen["argv"][seen["argv"].index("--model") + 1] == "gpt-5.6-sol"
    assert seen["argv"][seen["argv"].index("--mcp-config") + 1] == ".pi/mcp.json"
    assert seen["argv"][-2:] == ["-p", seen["prompt_arg"]]
    assert seen["prompt_arg"].startswith("@.pi/turn-prompts/")
    assert prompt not in seen["argv"]
    assert all("\n" not in part for part in seen["argv"])
    assert seen["prompt_text"] == prompt
    assert not seen["prompt_path"].exists()


def test_pi_uses_only_the_explicit_mcp_adapter_in_production(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agent.pi_process.settings.pi_mcp_adapter_path",
        "/usr/local/lib/node_modules/pi-mcp-adapter/index.ts",
    )

    argv = _build_argv(prompt_arg="@.pi/turn-prompts/turn.md")

    assert "--no-extensions" in argv
    assert argv[argv.index("--extension") + 1] == (
        "/usr/local/lib/node_modules/pi-mcp-adapter/index.ts"
    )


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
