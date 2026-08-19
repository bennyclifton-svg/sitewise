import pytest

from ingest.embed import EMBED_MAX_TOKENS, EmbedInputTooLarge, embed_texts


def test_oversized_chunk_raises_a_named_error() -> None:
    huge = "word " * (EMBED_MAX_TOKENS + 50)
    with pytest.raises(EmbedInputTooLarge, match="mystery-drawing.pdf") as exc:
        embed_texts([huge], relative_paths=["mystery-drawing.pdf"])
    assert exc.value.relative_path == "mystery-drawing.pdf"
