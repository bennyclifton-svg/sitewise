from __future__ import annotations

from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, Field

EmailProviderName = Literal[
    "fake", "microsoft_graph", "gmail", "mailgun", "inbound_alias"
]


class RawProviderAttachment(BaseModel):
    provider_attachment_id: str
    filename: str
    content_type: str
    size_bytes: int


class RawProviderMessage(BaseModel):
    provider: EmailProviderName
    provider_message_id: str
    provider_thread_id: str | None = None
    internet_message_id: str | None = None
    from_address: str
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str
    sent_at: datetime | None = None
    body_text: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    attachments: list[RawProviderAttachment] = Field(default_factory=list)


class ProviderDraft(BaseModel):
    to_addresses: list[str]
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str
    body_text: str
    in_reply_to: str | None = None
    # Only providers that can send as an arbitrary address honour this. Gmail
    # and Graph always send as the connected mailbox and ignore it.
    from_address: str | None = None
    references: list[str] = Field(default_factory=list)


class LinkEmailRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=4000)


class EmailMatchView(BaseModel):
    email_id: uuid.UUID
    project_id: uuid.UUID | None
    match_basis: str | None
    match_confidence: float | None


class EmailDraftView(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str
    body_text: str
    in_reply_to_email_id: uuid.UUID | None
    provider_draft_id: str | None
    provider_message_id: str | None
    send_error: str | None
    sent_at: datetime | None
    sent_by_user_id: uuid.UUID | None


class ReplyEmailDraftRequest(BaseModel):
    body_text: str = ""
    to_addresses: list[str] | None = None
    cc_addresses: list[str] | None = None


class EmailRegisterRow(BaseModel):
    id: str
    kind: Literal["inbound", "outbound"]
    direction: Literal["in", "out"]
    subject: str
    party: str
    sent_at: datetime | None = None
    message_category: str | None = None
    status: str | None = None
    email_id: uuid.UUID | None = None
    draft_id: uuid.UUID | None = None
