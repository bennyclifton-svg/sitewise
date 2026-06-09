import uuid

from app.assistant.outputs import Citation, EvidenceLabel
from app.grounding.validator import GroundingValidator
from app.retrieval.catalog import CorpusProjectSummary, build_catalog_answer, catalog_to_passages


def test_build_catalog_answer_includes_all_projects() -> None:
    chunk_id = uuid.uuid4()
    document_id = uuid.uuid4()
    catalog = [
        CorpusProjectSummary(
            project="procurement-blockb",
            phase="procurement",
            source_type="project_evidence",
            document_count=42,
            sample_chunk_id=chunk_id,
            sample_document_id=document_id,
            sample_filename="brief.pdf",
            sample_relative_path="procurement-blockb/03 RFT/brief.pdf",
        )
    ]

    answer = build_catalog_answer(catalog)
    assert "procurement-blockb" in answer.answer
    assert len(answer.citations) == 1
    assert answer.citations[0].chunk_id == chunk_id


def test_catalog_passages_validate_project_excerpt() -> None:
    chunk_id = uuid.uuid4()
    document_id = uuid.uuid4()
    catalog = [
        CorpusProjectSummary(
            project="delivery-house",
            phase="delivery",
            source_type="project_evidence",
            document_count=5,
            sample_chunk_id=chunk_id,
            sample_document_id=document_id,
            sample_filename="contract.pdf",
            sample_relative_path="delivery-house/contract.pdf",
        )
    ]
    validator = GroundingValidator()
    validator.register(catalog_to_passages(catalog))

    from app.assistant.outputs import GroundedAnswer

    answer = GroundedAnswer(
        answer="delivery-house is indexed.",
        citations=[
            Citation(
                chunk_id=chunk_id,
                document_id=document_id,
                excerpt="Corpus project: delivery-house",
                filename="contract.pdf",
                project="delivery-house",
                source_type="project_evidence",
                label=EvidenceLabel.FACT,
            )
        ],
    )
    validated = validator.validate(answer)
    assert validated.cited_passages
