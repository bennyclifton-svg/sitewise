import asyncio
import selectors
import sys

import app.database.models  # noqa: F401 — register all ORM mappers before tests


def run_async(coro):
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return asyncio.run(coro)
