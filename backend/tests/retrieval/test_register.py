import uuid
from types import SimpleNamespace

from sqlalchemy import select

from app.database.source_document import SourceDocument
from app.projects.classification_override import classification_from_override
from app.retrieval.register import DrawingRegisterRow, _metadata_text, list_drawings
from ingest.types import Classification
from tests.conftest import run_async


def test_list_drawings_sql_requires_drawing_class() -> None:
    captured: dict[str, str] = {}

    class _Result:
        def all(self):
            return []

    class _Session:
        async def execute(self, stmt):
            captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            return _Result()

    run_async(list_drawings(_Session()))
    sql = captured["sql"].lower()
    assert "document_class" in sql
    assert "'drawing'" in sql or "drawing" in sql


def test_report_named_plan_is_not_selected_by_drawing_class_filter() -> None:
    stmt = select(SourceDocument.id).where(SourceDocument.document_class == "drawing")
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "drawing" in sql.lower()
    assert "site plan" not in sql.lower()


def test_drawing_with_title_block_populates_register_fields() -> None:
    metadata = {
        "drawing_number": "A101",
        "revision": "C02",
        "title": "Ground floor plan",
    }
    row = DrawingRegisterRow(
        document_id=uuid.uuid4(),
        filename="A101.pdf",
        relative_path="03-design/architectural/A101.pdf",
        project="demo",
        phase="delivery",
        drawing_number=_metadata_text(metadata, "drawing_number"),
        revision=_metadata_text(metadata, "revision"),
        title=_metadata_text(metadata, "title"),
    )
    assert row.drawing_number == "A101"
    assert row.revision == "C02"
    assert row.title == "Ground floor plan"


def test_overridden_drawing_keeps_title_block_in_register() -> None:
    machine = Classification(
        document_class="drawing",
        document_subject="none",
        ingest_mode="full_text",
        document_metadata={
            "basis": "structural",
            "confidence": "0.95",
            "subject": "none",
            "drawing_number": "S101",
            "revision": "A",
            "title": "Foundation Plan",
        },
        confidence=0.95,
        basis="structural",
    )
    merged = classification_from_override(
        SimpleNamespace(document_class="drawing", document_subject="structural"),
        machine=machine,
    )
    row = DrawingRegisterRow(
        document_id=uuid.uuid4(),
        filename="S101-Foundation-Plan.pdf",
        relative_path="03-design/structural/S101-Foundation-Plan.pdf",
        project="demo",
        phase="delivery",
        drawing_number=_metadata_text(merged.document_metadata, "drawing_number"),
        revision=_metadata_text(merged.document_metadata, "revision"),
        title=_metadata_text(merged.document_metadata, "title"),
    )
    assert row.drawing_number == "S101"
    assert row.revision == "A"
    assert row.title == "Foundation Plan"
