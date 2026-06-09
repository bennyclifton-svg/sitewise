import uuid

from app.assistant.agent import repair_missing_platform_citations
from app.assistant.outputs import GroundedAnswer
from app.retrieval.schemas import SourcePassage


def test_repair_missing_platform_citations_prefers_doctrine() -> None:
    doctrine_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    passages = [
        SourcePassage(
            chunk_id=seed_id,
            document_id=seed_id,
            chunk_index=0,
            content="Seed mention of PMP.",
            page_or_section=None,
            project="sitewise-platform",
            phase="reference",
            source_type="reference",
            document_class="reference_guide",
            filename="seed.md",
            relative_path="seed/seed.md",
            document_metadata={"knowledge_scope": "platform"},
            chunk_metadata={"whole_document": True},
            score=5.0,
        ),
        SourcePassage(
            chunk_id=doctrine_id,
            document_id=doctrine_id,
            chunk_index=0,
            content="Doctrine defines the PMP programme section.",
            page_or_section=None,
            project="sitewise-platform",
            phase="reference",
            source_type="doctrine",
            document_class="doctrine",
            filename="clerk-brief.md",
            relative_path="docs/clerk-brief.md",
            document_metadata={"knowledge_scope": "platform"},
            chunk_metadata={"whole_document": True},
            score=1.0,
        ),
    ]
    answer = GroundedAnswer(
        answer="A PMP is a project management plan.",
        evidence_sufficient=True,
    )

    repaired = repair_missing_platform_citations(answer, passages)

    assert len(repaired.citations) == 1
    assert repaired.citations[0].chunk_id == doctrine_id
    assert repaired.citations[0].filename == "clerk-brief.md"
