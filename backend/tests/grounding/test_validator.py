import uuid

import pytest

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.grounding.validator import GroundingError, GroundingValidator
from app.retrieval.schemas import SourcePassage


def _passage(
    *,
    chunk_id: uuid.UUID | None = None,
    content: str = "Progress must be certified only after inspection.",
) -> SourcePassage:
    chunk_id = chunk_id or uuid.uuid4()
    document_id = uuid.uuid4()
    return SourcePassage(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        content=content,
        page_or_section="§07",
        project="clerk",
        phase="doctrine",
        source_type="doctrine",
        document_class="doctrine",
        filename="clerk-brief.md",
        relative_path="docs/clerk-brief.md",
        document_metadata=None,
        chunk_metadata=None,
        score=1.0,
    )


def test_validate_attaches_cited_passages() -> None:
    passage = _passage()
    validator = GroundingValidator()
    validator.register([passage])

    answer = GroundedAnswer(
        answer="Doctrine requires inspection before certification.",
        citations=[
            Citation(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                excerpt="certified only after inspection",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
                page_or_section=passage.page_or_section,
                label=EvidenceLabel.FACT,
            )
        ],
    )

    validated = validator.validate(answer)
    assert len(validated.cited_passages) == 1
    assert validated.cited_passages[0].chunk_id == passage.chunk_id


def test_validate_allows_insufficient_evidence_without_citations() -> None:
    validator = GroundingValidator()
    answer = GroundedAnswer(
        answer="The corpus does not contain enough evidence to answer.",
        evidence_sufficient=False,
    )
    validated = validator.validate(answer)
    assert validated.cited_passages == []


def test_validate_rejects_uncited_sufficient_answer() -> None:
    validator = GroundingValidator()
    answer = GroundedAnswer(
        answer="The TRR recommends Tenderer 01.",
        evidence_sufficient=True,
        citations=[],
    )
    with pytest.raises(GroundingError, match="no citations"):
        validator.validate(answer)


def test_validate_rejects_unretrieved_chunk_id() -> None:
    passage = _passage()
    validator = GroundingValidator()
    validator.register([passage])
    other_chunk = uuid.uuid4()

    answer = GroundedAnswer(
        answer="Claim with bad citation.",
        citations=[
            Citation(
                chunk_id=other_chunk,
                document_id=passage.document_id,
                excerpt="after inspection",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
            )
        ],
    )
    with pytest.raises(GroundingError, match="not retrieved"):
        validator.validate(answer)


def test_validate_rejects_excerpt_not_in_passage() -> None:
    passage = _passage(content="Actual passage text only here.")
    validator = GroundingValidator()
    validator.register([passage])

    answer = GroundedAnswer(
        answer="Claim.",
        citations=[
            Citation(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                excerpt="completely different text",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
            )
        ],
    )
    validated = validator.validate(answer)
    assert validated.citations[0].excerpt.startswith("Actual passage")


def test_repair_truncated_excerpt_with_ellipsis() -> None:
    passage = _passage(
        content="TENDER EVALUATION PLAN \n\ntender evaluation committee\n\nNick Payne YMCA"
    )
    validator = GroundingValidator()
    validator.register([passage])

    answer = GroundedAnswer(
        answer="Committee listed.",
        citations=[
            Citation(
                chunk_id=passage.chunk_id,
                document_id=passage.document_id,
                excerpt="TENDER EVALUATION PLAN \n\ntender evaluation committee\n\nNick Payne...",
                filename=passage.filename,
                project=passage.project,
                source_type=passage.source_type,
            )
        ],
    )
    validated = validator.validate(answer)
    assert validated.cited_passages
