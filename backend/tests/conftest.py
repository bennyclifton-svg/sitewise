import asyncio
import selectors
import sys
import tempfile
from pathlib import Path

import app.database.models  # noqa: F401 — register all ORM mappers before tests


def pytest_configure(config):
    # Fresh basetemp per run: shared roots (pytest-of-<user>, a fixed --basetemp)
    # break on Windows when sandboxed agent runs create them with ACLs the next
    # run's identity cannot delete.
    if config.option.basetemp is None:
        config.option.basetemp = Path(tempfile.mkdtemp(prefix="clerk-pytest-"))


def run_async(coro):
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return asyncio.run(coro)
