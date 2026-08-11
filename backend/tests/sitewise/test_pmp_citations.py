from app.sitewise.pmp_citations import (
    build_citation_index,
    format_citation_key_lines,
)


def test_build_citation_index_numbers_documents_in_stable_path_order() -> None:
    index = build_citation_index(
        [
            ("02-evidence/fee-proposal.pdf", "2026-03-01"),
            ("02-evidence/engagement-letter.pdf", "executed"),
            ("02-evidence/owner-brief.pdf", "draft"),
        ]
    )
    assert index.number_for("02-evidence/engagement-letter.pdf") == 1
    assert index.number_for("02-evidence/fee-proposal.pdf") == 2
    assert index.token_for("02-evidence/owner-brief.pdf") == "[3]"
    assert index.token_for("missing.pdf") == "—"


def test_citation_key_lines_are_short_and_numbered() -> None:
    index = build_citation_index(
        [("docs/b.pdf", "on file"), ("docs/a.pdf", "2026-01-01")]
    )
    assert format_citation_key_lines(index) == [
        "- [1] a.pdf — 2026-01-01",
        "- [2] b.pdf — on file",
    ]


def test_empty_corpus_has_no_numbers() -> None:
    index = build_citation_index([])
    assert index.documents == ()
    assert index.token_for("anything") == "—"


def test_build_citation_index_keeps_first_duplicate_path() -> None:
    index = build_citation_index(
        [
            ("docs/a.pdf", "2026-01-01"),
            ("docs/a.pdf", "superseded"),
            ("docs/b.pdf", "on file"),
        ]
    )
    assert index.documents == (("docs/a.pdf", "2026-01-01"), ("docs/b.pdf", "on file"))
    assert index.number_for("docs/a.pdf") == 1
    assert format_citation_key_lines(index) == [
        "- [1] a.pdf — 2026-01-01",
        "- [2] b.pdf — on file",
    ]


def test_build_citation_index_normalises_backslashes() -> None:
    index = build_citation_index(
        [("docs\\b.pdf", "on file"), ("docs/a.pdf", "2026-01-01")]
    )
    assert index.documents == (("docs/a.pdf", "2026-01-01"), ("docs/b.pdf", "on file"))
    assert index.number_for("docs\\b.pdf") == 2
    assert format_citation_key_lines(index) == [
        "- [1] a.pdf — 2026-01-01",
        "- [2] b.pdf — on file",
    ]
