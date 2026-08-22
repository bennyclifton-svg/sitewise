"""Project email register merges inbound mail with outbound drafts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.email.service import merge_email_register


def test_register_sorts_inbound_and_outbound_by_sent_at() -> None:
    inbound_id = uuid.uuid4()
    draft_id = uuid.uuid4()
    rows = merge_email_register(
        [
            {
                "email_id": str(inbound_id),
                "from_address": "qs@consultant.com",
                "subject": "RFI-12 slab thickness",
                "sent_at": "2026-08-14T00:00:00+00:00",
                "message_category": "rfi",
            }
        ],
        [
            SimpleNamespace(
                id=draft_id,
                to_addresses=["qs@consultant.com"],
                subject="Re: RFI-12 slab thickness",
                sent_at=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
                status="sent",
                in_reply_to_email_id=inbound_id,
            )
        ],
    )

    assert [row["direction"] for row in rows] == ["out", "in"]
    assert rows[0]["kind"] == "outbound"
    assert rows[0]["draft_id"] == str(draft_id)
    assert rows[0]["party"] == "qs@consultant.com"
    assert rows[1]["kind"] == "inbound"
    assert rows[1]["email_id"] == str(inbound_id)
    assert rows[1]["message_category"] == "rfi"


def test_unsent_drafts_sort_ahead_of_dated_mail() -> None:
    rows = merge_email_register(
        [
            {
                "email_id": str(uuid.uuid4()),
                "from_address": "builder@trade.com",
                "subject": "Progress claim 04",
                "sent_at": "2026-08-10T00:00:00+00:00",
                "message_category": "invoice_notice",
            }
        ],
        [
            SimpleNamespace(
                id=uuid.uuid4(),
                to_addresses=["builder@trade.com"],
                subject="Re: Progress claim 04",
                sent_at=None,
                status="draft",
                in_reply_to_email_id=None,
            )
        ],
    )

    assert rows[0]["status"] == "draft"
    assert rows[0]["direction"] == "out"
    assert rows[1]["direction"] == "in"
