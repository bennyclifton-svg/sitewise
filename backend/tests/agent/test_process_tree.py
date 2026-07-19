import asyncio
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from app.agent.process_tree import subprocess_group_options, terminate_process_tree


def run_async(coro):
    return asyncio.run(coro)


class _ProcessAdapter:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def returncode(self) -> int | None:
        return self._process.poll()

    async def wait(self) -> int:
        return await asyncio.to_thread(self._process.wait)

    def kill(self) -> None:
        self._process.kill()


def _process_exists(pid: int) -> bool:
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _wait_for_file(path: Path, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"child pid file was not created: {path}")
        await asyncio.sleep(0.02)


@pytest.mark.parametrize("lifecycle", ["stop", "disconnect", "timeout", "cancellation"])
def test_terminate_process_tree_removes_parent_and_descendant(
    tmp_path: Path, lifecycle: str
) -> None:
    pid_file = tmp_path / "child.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import pathlib, subprocess, sys, time; "
        f"child=subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
        "time.sleep(60)"
    )

    async def _run() -> tuple[int, int]:
        spawned = subprocess.Popen(
            [sys.executable, "-c", parent_code, str(pid_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **subprocess_group_options(),
        )
        parent = _ProcessAdapter(spawned)
        await _wait_for_file(pid_file)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        await terminate_process_tree(parent, grace_seconds=1.0)
        return parent.pid, child_pid

    parent_pid, child_pid = run_async(_run())
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and (
        _process_exists(parent_pid) or _process_exists(child_pid)
    ):
        time.sleep(0.02)

    assert not _process_exists(parent_pid)
    assert not _process_exists(child_pid)


@pytest.mark.skipif(os.name == "nt", reason="POSIX process groups survive parent exit")
@pytest.mark.parametrize("exit_code", [0, 7], ids=["success", "failure"])
def test_cleanup_removes_descendant_after_parent_exit(
    tmp_path: Path, exit_code: int
) -> None:
    pid_file = tmp_path / f"exited-parent-{exit_code}.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import pathlib, subprocess, sys; "
        f"child=subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
        f"raise SystemExit({exit_code})"
    )

    async def _run() -> tuple[int, int]:
        spawned = subprocess.Popen(
            [sys.executable, "-c", parent_code, str(pid_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **subprocess_group_options(),
        )
        parent = _ProcessAdapter(spawned)
        await _wait_for_file(pid_file)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        await parent.wait()
        await terminate_process_tree(parent, grace_seconds=0.2)
        return parent.pid, child_pid

    parent_pid, child_pid = run_async(_run())
    assert not _process_exists(parent_pid)
    assert not _process_exists(child_pid)


def test_subprocess_group_options_is_platform_specific() -> None:
    options = subprocess_group_options()
    if os.name == "nt":
        assert options == {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        assert options == {"start_new_session": True}


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group escalation")
def test_terminate_process_tree_kills_descendant_that_ignores_sigterm(
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "stubborn-child.pid"
    child_code = (
        "import signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(60)"
    )
    parent_code = (
        "import pathlib, subprocess, sys, time; "
        f"child=subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
        "time.sleep(60)"
    )

    async def _run() -> tuple[int, int]:
        spawned = subprocess.Popen(
            [sys.executable, "-c", parent_code, str(pid_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **subprocess_group_options(),
        )
        parent = _ProcessAdapter(spawned)
        await _wait_for_file(pid_file)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        await terminate_process_tree(parent, grace_seconds=0.2)
        return parent.pid, child_pid

    parent_pid, child_pid = run_async(_run())
    assert not _process_exists(parent_pid)
    assert not _process_exists(child_pid)
