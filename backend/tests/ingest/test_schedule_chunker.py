from ingest.chunkers.schedule import chunk_schedule
from ingest.router import _chunker_for
from ingest.types import Classification


_TABLE = """
| Item | Duration |
| --- | --- |
| Site establishment | 5 days |
| Demolition | 10 days |
| Structure | 20 days |
"""


def test_schedule_table_emits_one_chunk_per_row() -> None:
    chunks = chunk_schedule(
        _TABLE,
        source_format="md",
        relative_path="04-projects/demo/06-programme/master.md",
    )
    bodies = [chunk.content for chunk in chunks]
    assert any("Site establishment" in body for body in bodies)
    assert any("Demolition" in body for body in bodies)
    assert any("Structure" in body for body in bodies)
    assert len(chunks) == 3
    assert {chunk.page_or_section for chunk in chunks} == {"row 1", "row 2", "row 3"}


def test_schedule_class_uses_schedule_chunker() -> None:
    classification = Classification(
        document_class="schedule",
        document_subject="none",
        ingest_mode="full_text",
        document_metadata={"basis": "filename", "confidence": "0.90", "subject": "none"},
        confidence=0.90,
        basis="filename",
    )
    assert _chunker_for(classification) == "schedule"
