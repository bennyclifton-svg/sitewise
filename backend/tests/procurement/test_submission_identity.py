import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai import OpenAIError

from app.procurement import submission_identity as service
from tests.conftest import run_async


def _identify(monkeypatch, contents, issuers, *, error=None):
    project_id = uuid.uuid4()
    files = [SimpleNamespace(id=uuid.uuid4(), source_document_id=uuid.uuid4(), ingest_status="ingested") for _ in contents]
    sources = [SimpleNamespace(id=file.source_document_id, normalized_content=content) for file, content in zip(files, contents)]
    monkeypatch.setattr(service, "resolve_submission_files", AsyncMock(return_value=files))
    extracted = service.SubmissionIssuers(documents=[
        service.DocumentIssuer(file_id=str(file.id), company_name=name, evidence_quote=quote)
        for file, (name, quote) in zip(files, issuers)
    ])
    extract = AsyncMock(return_value=extracted, side_effect=error)
    monkeypatch.setattr(service, "extract_identities", extract)
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: sources))))
    result = run_async(service.identify_submission_firm(session, project_id=project_id, file_ids=[file.id for file in files]))
    return result, extract


def test_returns_evidenced_issuer(monkeypatch):
    result, _ = _identify(monkeypatch, ["Client: Homeowner\nPrepared by Alder Engineers"], [("Alder Engineers", "Prepared by Alder Engineers")])
    assert result.status == "identified"
    assert result.company_name == "Alder Engineers"


@pytest.mark.parametrize("name,quote", [("Invented Firm", "Prepared by Invented Firm"), ("Ald", "Prepared by Alder"), ("Alder", None), (None, None)])
def test_requires_source_support_or_manual_name(monkeypatch, name, quote):
    result, _ = _identify(monkeypatch, ["Prepared by Alder"], [(name, quote)])
    assert result.status == "needs_name"
    assert result.company_name is None


def test_different_issuers_cannot_be_grouped(monkeypatch):
    result, _ = _identify(monkeypatch, ["Prepared by Alder", "Prepared by Birch"], [("Alder", "Prepared by Alder"), ("Birch", "Prepared by Birch")])
    assert result.status == "different_firms"


def test_multiple_documents_can_identify_the_same_firm(monkeypatch):
    result, _ = _identify(monkeypatch, ["Prepared by Alder", "Issued by ALDER"], [("Alder", "Prepared by Alder"), ("ALDER", "Issued by ALDER")])
    assert result.status == "identified"


def test_unread_document_does_not_call_model(monkeypatch):
    result, extract = _identify(monkeypatch, [""], [(None, None)])
    assert result.status == "needs_name"
    extract.assert_not_awaited()


def test_model_failure_allows_manual_linking(monkeypatch):
    result, _ = _identify(monkeypatch, ["Prepared by Alder"], [], error=OpenAIError("Unavailable"))
    assert result.status == "needs_name"
    assert "try again" in result.message


def test_incomplete_extraction_does_not_autofill(monkeypatch):
    result, _ = _identify(monkeypatch, ["Prepared by Alder", "Unreadable attachment"], [("Alder", "Prepared by Alder")])
    assert result.status == "needs_name"
