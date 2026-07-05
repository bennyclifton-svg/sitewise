from app.sitewise.mobilisation_evidence import MobilisationEvidencePack, merge_evidence_packs
from app.workflows.create_pmp import CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS


def test_merge_evidence_packs_handles_100_document_batches() -> None:
    merged = MobilisationEvidencePack()
    for index in range(100):
        batch_index = index // CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS
        merged = merge_evidence_packs(
            merged,
            MobilisationEvidencePack(
                other_evidence=[f"Batch {batch_index} document {index} on file"],
                evidence_refs=[f"project_evidence:04-projects/demo/doc-{index}.md#chunk={index}"],
            ),
        )

    assert len(merged.other_evidence) == 100
    assert len(merged.evidence_refs) == 100


def test_100_document_corpus_requires_thirteen_extraction_batches() -> None:
    assert (100 + CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS - 1) // (
        CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS
    ) == 13
