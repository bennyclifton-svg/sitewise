import asyncio
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only event loop policy")
def test_uvicorn_uses_selector_loop_on_windows() -> None:
    import uvicorn.loops.asyncio as uvicorn_asyncio_loop

    assert uvicorn_asyncio_loop.asyncio_loop_factory() is asyncio.SelectorEventLoop
