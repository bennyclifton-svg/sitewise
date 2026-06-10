"""Reset the ingested retrieval corpus (DB only -- never touches data/ files).

    cd backend
    uv run python scripts/reset_corpus.py            # dry run: show current corpus
    uv run python scripts/reset_corpus.py --execute  # TRUNCATE corpus tables

Truncates message_citations, document_chunks, and source_documents. Files under
data/ are left untouched, so the lean set can be re-ingested with the ingest CLI.
"""

import asyncio
import selectors
import sys
from pathlib import Path

# Allow running as `python scripts/reset_corpus.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.database.models  # noqa: F401
from sqlalchemy import func, select, text

from app.database.session import get_session_factory
from app.database.source_document import SourceDocument
from app.database.document_chunk import DocumentChunk


async def _print_corpus(session) -> None:
    doc_count = await session.scalar(select(func.count(SourceDocument.id)))
    chunk_count = await session.scalar(select(func.count(DocumentChunk.id)))
    print(f"source_documents={doc_count}  document_chunks={chunk_count}", flush=True)

    per_project = await session.execute(
        select(SourceDocument.project, func.count(SourceDocument.id))
        .group_by(SourceDocument.project)
        .order_by(SourceDocument.project)
    )
    rows = per_project.all()
    if not rows:
        print("  (no projects ingested)", flush=True)
    for project, count in rows:
        print(f"  - {project}: {count} documents", flush=True)


async def main(execute: bool) -> None:
    factory = get_session_factory()
    async with factory() as session:
        print("=== current corpus ===", flush=True)
        await _print_corpus(session)

        if not execute:
            print("\nDry run. Re-run with --execute to truncate.", flush=True)
            return

        print("\nTruncating message_citations, document_chunks, source_documents ...", flush=True)
        await session.execute(text("SET statement_timeout = 0"))
        await session.execute(
            text("TRUNCATE message_citations, document_chunks, source_documents CASCADE")
        )
        await session.commit()

        print("\n=== corpus after reset ===", flush=True)
        await _print_corpus(session)


if __name__ == "__main__":
    run_execute = "--execute" in sys.argv[1:]
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        loop.run_until_complete(main(run_execute))
    else:
        asyncio.run(main(run_execute))
