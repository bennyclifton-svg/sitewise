from pathlib import Path
from unittest.mock import Mock

import pytest

from ingest import pipeline
from ingest.classify import classify_entry
from ingest.persist import _merged_metadata
from ingest.router import build_ingest_plan
from ingest.types import Classification, ManifestEntry, ProjectContext


CORPUS = Path(__file__).resolve().parents[3] / "docs/demo-corpus/seven-hills"
PROPOSALS = sorted((CORPUS / "02-consultant-procurement").glob("*/proposals/*.md"))


@pytest.fixture(autouse=True)
def _fresh_intake(monkeypatch):
    # These extraction fixtures represent new documents, without a database.
    monkeypatch.setattr(pipeline, "is_unchanged", lambda plan: False)


@pytest.mark.parametrize("source", PROPOSALS, ids=lambda path: path.stem)
def test_intake_classifies_extracted_proposal_and_its_proponent(source, monkeypatch):
    entry = ManifestEntry(source, f"04-projects/test/_inbox/{source.name}",
                          "test", source.name, ".md", source.stat().st_size)
    context = ProjectContext(project="test", phase="design", source_type="project_evidence")
    plan = build_ingest_plan(entry, context, classify_entry(entry))
    persist = Mock(return_value=True)
    monkeypatch.setattr(pipeline, "persist_ingest", persist)
    monkeypatch.setattr(pipeline, "embed_texts", lambda texts, **kwargs: [[0.0] for _ in texts])
    assert pipeline.ingest_plan(plan)
    saved, extracted = persist.call_args.args[:2]
    assert saved.classification.document_class == "commercial"
    metadata = _merged_metadata(saved, extracted)
    expected = next(line.split("|")[2].strip() for line in source.read_text(encoding="utf-8").splitlines()
                    if line.startswith("| Proponent |"))
    assert metadata["issuing_firm"] == expected
    assert metadata["commercial_type"] == "fee_proposal"
    expected_subject = {
        "architectural-services": "architect", "building-services-engineering": "none",
        "civil-stormwater-engineering": "civil", "structural-engineering": "structural",
        "town-planning": "town_planner",
    }[source.parent.parent.name]
    assert metadata["subject"] == expected_subject


def test_post_extraction_classification_preserves_user_correction(monkeypatch):
    source = PROPOSALS[0]
    entry = ManifestEntry(source, "04-projects/test/_inbox/attachment.md", "test",
                          "attachment.md", ".md", source.stat().st_size)
    context = ProjectContext(project="test", phase="design", source_type="project_evidence")
    correction = Classification(document_class="report", ingest_mode="full_text",
                                document_subject="architect", basis="user", confidence=1.0)
    persist = Mock(return_value=True)
    monkeypatch.setattr(pipeline, "persist_ingest", persist)
    monkeypatch.setattr(pipeline, "embed_texts", lambda texts, **kwargs: [[0.0] for _ in texts])
    assert pipeline.ingest_plan(build_ingest_plan(entry, context, correction))
    saved = persist.call_args.args[0].classification
    assert saved.document_class == "report"
    assert saved.basis == "user"
    assert saved.document_subject == "architect"
