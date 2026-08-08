from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

from app.database.web_citations import persist_message_web_citations
from tests.conftest import run_async


def test_persist_message_web_citations_maps_durable_provenance() -> None:
    session = Mock()
    project_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    message_id = uuid.uuid4()

    run_async(
        persist_message_web_citations(
            session,
            project_id=project_id,
            turn_id=turn_id,
            message_id=message_id,
            sources=[
                {
                    "url": "https://www.legislation.qld.gov.au/current-act",
                    "title": "Planning Act 2016",
                    "publisher": "Queensland Government",
                    "jurisdiction": "QLD",
                    "authority_class": "official_legislation",
                    "source_type": "web_legislation",
                    "version_status": "current",
                    "effective_date": "29 November 2024",
                    "section": "section 8",
                    "excerpt": "A planning instrument sets out policies.",
                    "content_hash": "a" * 64,
                    "retrieved_at": "2026-08-08T10:00:00+00:00",
                }
            ],
        )
    )

    citation = session.add.call_args.args[0]
    assert citation.project_id == project_id
    assert citation.turn_id == turn_id
    assert citation.message_id == message_id
    assert citation.source_type == "web_legislation"
    assert citation.excerpt.startswith("A planning instrument")
    assert citation.retrieved_at == datetime(2026, 8, 8, 10, tzinfo=UTC)
