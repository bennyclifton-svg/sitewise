"""Cross-platform process-group lifecycle for agent runtimes."""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Protocol


class GroupProcess(Protocol):
    returncode: int | None

    async def wait(self) -> int: ...
    def kill(self) -> None: ...


def subprocess_group_options() -> dict[str, object]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


async def _wait(process: GroupProcess, timeout: float) -> bool:
    try:
        await asyncio.wait_for(asyncio.shield(process.wait()), timeout=timeout)
        return True
    except TimeoutError:
        return False


def _posix_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def _wait_for_posix_group_exit(process_group_id: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while _posix_group_exists(process_group_id):
        if time.monotonic() >= deadline:
            return False
        await asyncio.sleep(0.02)
    return True


async def terminate_process_tree(
    process: GroupProcess, *, grace_seconds: float = 2.0
) -> None:
    """Terminate the isolated runtime group and await complete process exit."""
    pid = getattr(process, "pid", None)
    if isinstance(pid, int) and pid > 0:
        if os.name == "nt":
            # Ask Windows to terminate the complete tree while the parent/child
            # relationship still exists; waiting for the parent first can orphan
            # descendants before a forced tree kill can discover them.
            await asyncio.to_thread(
                subprocess.run,
                ["taskkill", "/PID", str(pid), "/T"],
                check=False,
                capture_output=True,
            )
        else:
            import signal

            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    else:
        process.kill()

    parent_exited = await _wait(process, grace_seconds)
    if os.name != "nt" and isinstance(pid, int) and pid > 0:
        if await _wait_for_posix_group_exit(pid, grace_seconds):
            return
    elif parent_exited:
        return

    if isinstance(pid, int) and pid > 0:
        if os.name == "nt":
            await asyncio.to_thread(
                subprocess.run,
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
            )
        else:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    else:
        process.kill()
    if not parent_exited:
        await process.wait()
    if os.name != "nt" and isinstance(pid, int) and pid > 0:
        await _wait_for_posix_group_exit(pid, grace_seconds)
