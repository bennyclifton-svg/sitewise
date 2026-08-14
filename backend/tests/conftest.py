import asyncio
import selectors
import sys
import tempfile
from pathlib import Path

from tests.offline_network import (
    OFFLINE_NETWORK_GUARD,
    startup_database_access_target,
    startup_network_access_permitted,
)

# These imports must follow offline_network: app settings read backend/.env at
# import time, and collected test modules may import HTTP/database libraries.
import pytest  # noqa: E402

import app.database.models  # noqa: E402, F401 — register ORM mappers after containment


def pytest_configure(config):
    # Fresh basetemp per run: shared roots (pytest-of-<user>, a fixed --basetemp)
    # break on Windows when sandboxed agent runs create them with ACLs the next
    # run's identity cannot delete.
    if config.option.basetemp is None:
        config.option.basetemp = Path(tempfile.mkdtemp(prefix="clerk-pytest-"))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    marker_names = {marker.name for marker in item.iter_markers()}
    lease = OFFLINE_NETWORK_GUARD.begin_test(
        allowed=startup_network_access_permitted(marker_names),
        database_target=startup_database_access_target(marker_names),
    )
    try:
        return (yield)
    finally:
        OFFLINE_NETWORK_GUARD.end_test(lease)


def run_async(coro):
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return asyncio.run(coro)
