from ingest.chunkers.prose import chunk_prose, count_tokens


def test_chunk_markdown_respects_headers():
    text = "# Intro\n\nHello.\n\n## Details\n\n" + ("word " * 400)
    chunks = chunk_prose(text, source_format="markdown", relative_path="seed/guide.md")
    assert chunks[0].page_or_section == "Intro"
    assert all(chunk.token_count <= 600 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_stable_chunk_indices_are_sequential():
    chunks = chunk_prose("short text", source_format="markdown", relative_path="a/b.md")
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_overlap_produces_multiple_chunks():
    long_text = "sentence. " * 500
    chunks = chunk_prose(long_text, source_format="pdf", relative_path="x/y.pdf")
    assert len(chunks) > 1
    assert count_tokens(chunks[0].content) <= 600
