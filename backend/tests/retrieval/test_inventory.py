import uuid

from app.chat.intent import (
    is_drawing_register_question,
    platform_inventory_scope,
)
from app.retrieval.inventory import (
    PlatformDocumentRow,
    build_seed_inventory_answer,
    platform_rows_to_passages,
)


def test_platform_inventory_scope_seed_listing() -> None:
    assert (
        platform_inventory_scope("list the seed knowledge files you have ingested")
        == "seed"
    )
    assert platform_inventory_scope("what seed guides are indexed?") == "seed"


def test_platform_inventory_scope_all_platform() -> None:
    assert platform_inventory_scope("list platform knowledge documents") == "all"


def test_platform_inventory_scope_not_content_question() -> None:
    assert platform_inventory_scope("what does the seed guide say about defects?") is None


def test_drawing_register_question() -> None:
    assert is_drawing_register_question("list the drawings on this project")
    assert not is_drawing_register_question("what does drawing H-102 show?")


def test_build_seed_inventory_answer_lists_paths() -> None:
    document_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    rows = [
        PlatformDocumentRow(
            document_id=document_id,
            filename="defects-and-dlp-guide.md",
            relative_path="seed/defects-and-dlp-guide.md",
            project="sitewise-platform",
            phase="reference",
            source_type="reference",
            document_class="reference_guide",
            knowledge_kind="seed",
        )
    ]
    answer = build_seed_inventory_answer(rows)
    assert "seed/defects-and-dlp-guide.md" in answer.answer
    assert len(answer.citations) == 1
    assert answer.citations[0].chunk_id == document_id


def test_platform_rows_to_passages_use_document_id_as_chunk_id() -> None:
    document_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    rows = [
        PlatformDocumentRow(
            document_id=document_id,
            filename="guide.md",
            relative_path="seed/guide.md",
            project="sitewise-platform",
            phase="reference",
            source_type="reference",
            document_class="reference_guide",
            knowledge_kind="seed",
        )
    ]
    passages = platform_rows_to_passages(rows)
    assert passages[0].chunk_id == document_id
