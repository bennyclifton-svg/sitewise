from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ingest.extract import extract_document
from ingest.extractors.base import ExtractedDocument


def test_unreadable_pdf_is_not_reported_as_an_unchanged_document() -> None:
    plan = SimpleNamespace(
        extractor="pdf_odl",
        entry=SimpleNamespace(absolute_path="synthetic.pdf", relative_path="synthetic.pdf"),
    )
    with patch.dict("ingest.extract._EXTRACTORS", {
        "pdf_odl": lambda _: ExtractedDocument(normalized_content="", page_count=2, pages=[]),
    }):
        with pytest.raises(ValueError, match="No readable text"):
            extract_document(plan)
