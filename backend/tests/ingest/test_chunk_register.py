from ingest.chunkers.prose import TARGET_TOKENS
from ingest.chunkers.register import chunk_register


def test_long_drawing_text_splits_into_bounded_chunks() -> None:
    text = "title block notes " * 2000
    chunks = chunk_register(
        text, source_format="pdf", relative_path="drawings/A-101.pdf"
    )
    assert len(chunks) > 1
    assert all((chunk.token_count or 0) <= TARGET_TOKENS for chunk in chunks)
    assert all(chunk.page_or_section == "register" for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
