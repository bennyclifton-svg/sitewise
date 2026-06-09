from ingest.discover import discover_corpus


def test_discover_builds_manifest(tmp_path):
    (tmp_path / "procurment-demo").mkdir()
    (tmp_path / "procurment-demo" / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "procurment-demo" / "skip.msg").write_bytes(b"x")

    entries = discover_corpus(tmp_path, folder="procurment-demo", supported_extensions={".pdf"})
    assert len(entries) == 1
    assert entries[0].extension == ".pdf"
    assert entries[0].relative_path == "procurment-demo/a.pdf"
