from types import SimpleNamespace

from scripts import x1_reclassify as reclassify


def test_reclassify_skips_user_basis_rows() -> None:
    doc = SimpleNamespace(
        document_class="unknown",
        document_metadata={"basis": "user", "subject": "none"},
        filename="scan.pdf",
        relative_path="04-projects/demo/_inbox/scan.pdf",
        project="demo",
        normalized_content="TAX INVOICE\nTotal $9,350",
        ingest_mode="full_text",
    )
    assert reclassify.reclassify_document(doc) is False
    assert doc.document_class == "unknown"


def test_reclassify_applies_stage_4_classifier_to_unknown_default() -> None:
    doc = SimpleNamespace(
        document_class="unknown",
        document_metadata={"basis": "default"},
        filename="Invoice 0043.pdf",
        relative_path="04-projects/demo/_inbox/Invoice 0043.pdf",
        project="demo",
        normalized_content="TAX INVOICE\nABN 12 345 678 901\nTotal $9,350",
        ingest_mode="register_only",
    )
    changed = reclassify.reclassify_document(doc)
    assert changed is True
    assert doc.document_class == "commercial"
    assert doc.document_metadata["machine_class"] == "commercial"
    assert doc.document_metadata["basis"] != "user"
