"""Run one chat turn in the terminal with full trace. Usage:

    cd backend
    uv run python scripts/debug_chat.py "What are the Block B evaluation criteria?"
"""

import asyncio
import selectors
import sys
import uuid
from pathlib import Path

# Allow running as `python scripts/debug_chat.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.database.models  # noqa: F401
from pydantic_ai.exceptions import ModelHTTPError

from app.chat.orchestrator import run_chat_turn
from app.config import settings
from app.database.session import get_session_factory
from app.grounding.validator import GroundingError


async def main(query: str) -> None:
    print(
        f"chat_model={settings.openai_chat_model} "
        f"(openai-chat:{settings.openai_chat_model})",
        flush=True,
    )
    print(f"embedding_model={settings.openai_embedding_model}", flush=True)
    print(f"query={query!r}", flush=True)

    factory = get_session_factory()
    async with factory() as session:
        try:
            answer = await run_chat_turn(
                session,
                user_id=uuid.uuid4(),
                thread_id=uuid.uuid4(),
                user_text=query,
            )
        except GroundingError as exc:
            print(f"GROUNDING FAILED: {exc}", flush=True)
            raise SystemExit(1) from exc
        except ModelHTTPError as exc:
            print(f"MODEL HTTP ERROR {exc.status_code}: {exc.body}", flush=True)
            raise SystemExit(1) from exc

    print("\n--- answer ---", flush=True)
    print(answer.answer, flush=True)
    print(f"\ncitations={len(answer.citations)}", flush=True)
    for citation in answer.citations:
        print(f"  - {citation.filename} ({citation.chunk_id})", flush=True)


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]).strip() or "What are the Block B evaluation criteria?"
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        loop.run_until_complete(main(text))
    else:
        asyncio.run(main(text))
