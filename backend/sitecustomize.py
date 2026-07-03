"""Process-wide Python startup tweaks for local backend tooling."""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy(),
    )
    try:
        import uvicorn.loops.asyncio as uvicorn_asyncio_loop
    except ImportError:
        pass
    else:
        uvicorn_asyncio_loop.asyncio_loop_factory = (
            lambda use_subprocess=False: asyncio.SelectorEventLoop
        )
