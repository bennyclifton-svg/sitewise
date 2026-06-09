from ingest.sanitize import sanitize_text


def test_strips_nul_bytes():
    assert sanitize_text("hello\x00world") == "helloworld"
