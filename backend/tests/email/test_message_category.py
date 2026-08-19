"""X1 Stage 18: email message_category is metadata, never a document_class."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from app.email.models import ProjectEmail
from ingest.types import DocumentClass, ManifestEntry

EMAIL_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SENT_AT = datetime(2026, 8, 19, 21, 0, tzinfo=UTC)


def _email(**overrides) -> ProjectEmail:
    fields = {
        "id": EMAIL_ID,
        "provider": "fake",
        "provider_message_id": "msg-1",
        "provider_thread_id": None,
        "internet_message_id": "<msg-1@example.com>",
        "from_address": "qs@consultant.com",
        "to_addresses": ["pm@owner.com"],
        "cc_addresses": [],
        "subject": "Hello",
        "sent_at": SENT_AT,
        "body_text": "",
        "headers": {},
        "content_hash": "a" * 64,
        "created_at": SENT_AT,
    }
    fields.update(overrides)
    return ProjectEmail(**fields)


def _entry(filename: str, *, extension: str) -> ManifestEntry:
    return ManifestEntry(
        absolute_path=Path(filename),
        relative_path=filename,
        project="kavanagh-residence",
        filename=filename,
        extension=extension,
        size_bytes=100,
    )


def test_message_category_is_not_a_document_class() -> None:
    from app.email.intelligence import MessageCategory

    categories = set(get_args(MessageCategory))
    classes = set(get_args(DocumentClass))
    assert len(categories) == 14
    assert "rfi" in categories
    assert "document_transmittal" in categories
    assert "rfi" not in classes
    assert "document_transmittal" not in classes
    assert "instruction" not in classes
    overlap = categories & classes
    assert overlap <= {"unknown"}


def test_transmittal_email_leaves_drawing_class_on_the_attachment() -> None:
    from ingest.classify import classify_entry

    from app.email.intelligence import classify_message_category

    email = _email(
        subject="Transmittal — S203 structural",
        body_text="Please find IFC drawings attached for construction.",
    )
    assert classify_message_category(email) == "document_transmittal"
    drawing = classify_entry(_entry("S203.pdf", extension=".pdf"))
    assert drawing.document_class == "drawing"
    assert drawing.document_class != "document_transmittal"


def test_rfi_email_body_is_correspondence_not_an_rfi_class() -> None:
    from ingest.classify import classify_entry

    from app.email.intelligence import classify_message_category

    email = _email(
        subject="RFI-012 — ceiling void clearance",
        body_text="Please advise the required clearance at grid C/4.",
    )
    assert classify_message_category(email) == "rfi"
    assert "rfi" not in get_args(DocumentClass)
    body_as_file = classify_entry(_entry("RFI-012.eml", extension=".eml"))
    assert body_as_file.document_class == "correspondence"
    assert body_as_file.document_class != "rfi"
