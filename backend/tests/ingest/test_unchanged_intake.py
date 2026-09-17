from dataclasses import replace
from unittest.mock import MagicMock, patch
import uuid

import pytest

from ingest.hashing import file_content_hash
from ingest.pipeline import ingest_plan, plan_entry
from ingest.types import ManifestEntry


@pytest.mark.parametrize("project_id", [None, uuid.UUID(int=1), uuid.UUID(int=2)])
@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("unchanged", [False, True])
def test_unchanged_replay_skips_expensive_work(tmp_path, project_id, force, unchanged):
    path = tmp_path / "guidance.md"
    path.write_text("Construction guidance. " * 100, encoding="utf-8")
    plan = plan_entry(ManifestEntry(path, "seed/guidance.md", "seed", path.name, ".md", path.stat().st_size))
    plan = replace(plan, context=replace(plan.context, project_id=project_id))
    session = MagicMock()
    session.scalar.return_value = file_content_hash(path) if unchanged else "previous-content-hash"
    factory = MagicMock()
    factory.return_value.__enter__.return_value = session
    traces = []
    with (
        patch("ingest.persist.get_sync_session_factory", return_value=factory),
        patch("ingest.pipeline.extract_document", return_value=MagicMock(
            normalized_content="Construction guidance. " * 100, pages=[], extraction_metadata={},
        )) as extract,
        patch("ingest.pipeline.chunk_document", return_value=[MagicMock(content="Evidence")]),
        patch("ingest.pipeline.embed_texts", return_value=[[0.1]]) as embed,
        patch("ingest.persist.upsert_document", return_value=uuid.UUID(int=3)),
        patch("ingest.persist.upsert_chunks"),
    ):
        result = ingest_plan(plan, skip_if_unchanged=not force, trace_callback=lambda *args: traces.append(args))
    should_process = force or not unchanged
    assert result is should_process
    assert extract.call_count == int(should_process)
    assert embed.call_count == int(should_process)
    if not force:
        query = session.scalar.call_args.args[0]
        params = query.compile().params
        assert "seed/guidance.md" in params.values()
        if project_id is None:
            assert "platform" in params.values()
            assert "IS NULL" in str(query)
        else:
            assert project_id in params.values()
        assert traces[-1][0:2] == ("persist", "complete" if should_process else "skipped")


def test_failed_unchanged_lookup_does_not_call_provider(tmp_path):
    path = tmp_path / "guidance.md"
    path.write_text("Evidence", encoding="utf-8")
    plan = plan_entry(ManifestEntry(path, "seed/guidance.md", "seed", path.name, ".md", 8))
    with (
        patch("ingest.persist.get_sync_session_factory", side_effect=RuntimeError("database unavailable")),
        patch("ingest.pipeline.extract_document") as extract,
    ):
        with pytest.raises(RuntimeError, match="database unavailable"):
            ingest_plan(plan)
    extract.assert_not_called()
