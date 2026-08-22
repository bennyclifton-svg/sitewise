"""Raw project email and derived interpretation (D5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

RAW_EMAIL_COLUMNS = frozenset(
    {
        "id",
        "mailbox_account_id",
        "provider",
        "provider_message_id",
        "provider_thread_id",
        "internet_message_id",
        "from_address",
        "to_addresses",
        "cc_addresses",
        "subject",
        "sent_at",
        "body_text",
        "headers",
        "raw_storage_key",
        "content_hash",
        "created_at",
    }
)


class RawEmailImmutable(RuntimeError):
    """Raised when a raw project_emails column is mutated after insert."""


class ProjectEmail(Base):
    """Immutable raw message. Interpretation lives on a sibling row."""

    __tablename__ = "project_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mailbox_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255))
    internet_message_id: Mapped[str | None] = mapped_column(String(255))
    from_address: Mapped[str] = mapped_column(String(320), nullable=False)
    to_addresses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cc_addresses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_storage_key: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    interpretation: Mapped[ProjectEmailInterpretation | None] = relationship(
        back_populates="email",
        cascade="all, delete-orphan",
        uselist=False,
    )
    attachments: Mapped[list[ProjectEmailAttachment]] = relationship(
        back_populates="email",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_message_id",
            name="uq_project_emails_provider_message",
        ),
        CheckConstraint(
            "provider IN ('fake','microsoft_graph','gmail','mailgun','inbound_alias')",
            name="ck_project_emails_provider",
        ),
    )


class ProjectEmailInterpretation(Base):
    """Derived overlay. Never replaces body_text or other raw columns."""

    __tablename__ = "project_email_interpretations"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_emails.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    match_basis: Mapped[str | None] = mapped_column(String(32))
    match_reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )
    message_category: Mapped[str | None] = mapped_column(String(32))
    summary: Mapped[str | None] = mapped_column(Text)
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    email: Mapped[ProjectEmail] = relationship(back_populates="interpretation")

    __table_args__ = (
        CheckConstraint(
            "match_basis IS NULL OR match_basis IN "
            "('contact','domain','thread','alias','subject','user','default')",
            name="ck_email_interpretations_match_basis",
        ),
        CheckConstraint(
            "match_confidence IS NULL OR "
            "(match_confidence >= 0 AND match_confidence <= 1)",
            name="ck_email_interpretations_match_confidence",
        ),
        CheckConstraint(
            "message_category IS NULL OR message_category IN ("
            "'action_required','decision_required','design_change','rfi',"
            "'instruction','programme_change','document_transmittal',"
            "'approval','invoice_notice','fee_proposal','tender_submission',"
            "'meeting','information_only','unknown'"
            ")",
            name="ck_email_interpretations_message_category",
        ),
    )


DRAFT_STATUSES = (
    "draft",
    "sending",
    "sent",
    "send_failed",
    "cancelled",
)


class ProjectEmailDraft(Base):
    """User-approved outbound draft. Creating one never sends (D7)."""

    __tablename__ = "project_email_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    in_reply_to_email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_emails.id", ondelete="SET NULL"),
    )
    to_addresses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cc_addresses: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provider_draft_id: Mapped[str | None] = mapped_column(String(255))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    send_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    references: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "status IN ('" + "','".join(DRAFT_STATUSES) + "')",
            name="ck_email_drafts_status",
        ),
    )


class ProjectEmailAttachment(Base):
    """Provider attachment references. Bytes are pulled in Stage 16."""

    __tablename__ = "project_email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_emails.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_attachment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
    )

    email: Mapped[ProjectEmail] = relationship(back_populates="attachments")

    __table_args__ = (
        UniqueConstraint(
            "email_id",
            "provider_attachment_id",
            name="uq_email_attachments_email_provider",
        ),
    )


@event.listens_for(ProjectEmail, "before_update")
def refuse_raw_email_orm_update(mapper, connection, target: ProjectEmail) -> None:
    state = inspect(target)
    for column in RAW_EMAIL_COLUMNS:
        history = state.attrs[column].history
        if history.has_changes():
            raise RawEmailImmutable(
                f"project_emails.{column} is immutable after insert"
            )
