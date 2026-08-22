"""Map Mailgun inbound multipart fields onto the Stage 22 ingest payload."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from email.utils import getaddresses, parseaddr
from typing import Any

MAILGUN_INBOUND_PATH = "/internal/email/inbound/mailgun"
MAILGUN_SIGNATURE_MAX_AGE_SECONDS = 600


def mailgun_signature_valid(
    *,
    signing_key: str,
    timestamp: str,
    token: str,
    signature: str,
) -> bool:
    if not signing_key or not timestamp or not token or not signature:
        return False
    expected = hmac.new(
        signing_key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def mailgun_timestamp_stale(
    timestamp: str,
    *,
    now: int,
    max_age_seconds: int = MAILGUN_SIGNATURE_MAX_AGE_SECONDS,
) -> bool:
    try:
        age = abs(now - int(timestamp))
    except ValueError:
        return True
    return age > max_age_seconds


def inbound_payload_from_mailgun(
    *,
    fields: Mapping[str, str],
    attachments: Sequence[tuple[str, bytes, str | None]],
) -> dict[str, Any]:
    headers = _headers(fields)
    to_addresses = _unique_addresses(
        fields.get("To") or fields.get("to") or "",
        fields.get("recipient") or "",
    )
    return {
        "from": _from_address(fields),
        "to": to_addresses,
        "cc": _unique_addresses(fields.get("Cc") or fields.get("cc") or ""),
        "bcc": [],
        "subject": fields.get("subject") or "",
        "sent_at": _sent_at(fields, headers),
        "body_text": (
            fields.get("body-plain")
            or fields.get("stripped-text")
            or fields.get("body-html")
            or ""
        ),
        "headers": headers,
        "attachments": [
            {
                "filename": filename,
                "content_base64": base64.b64encode(content).decode("ascii"),
                "content_type": content_type,
            }
            for filename, content, content_type in attachments
        ],
    }


def _from_address(fields: Mapping[str, str]) -> str:
    _, parsed = parseaddr((fields.get("from") or fields.get("sender") or "").strip())
    return parsed or (fields.get("sender") or fields.get("from") or "").strip()


def _unique_addresses(*values: str) -> list[str]:
    seen: set[str] = set()
    addresses: list[str] = []
    for value in values:
        for _, address in getaddresses([value]):
            normalized = address.strip()
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            addresses.append(normalized)
    return addresses


def _headers(fields: Mapping[str, str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    raw = fields.get("message-headers")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, list | tuple) or len(item) < 2:
                    continue
                name = str(item[0]).strip().lower()
                if name:
                    headers[name] = str(item[1])
    message_id = fields.get("Message-Id") or fields.get("Message-ID")
    if message_id and "message-id" not in headers:
        headers["message-id"] = message_id
    return headers


def _sent_at(fields: Mapping[str, str], headers: Mapping[str, str]) -> datetime | None:
    date_header = headers.get("date")
    if date_header:
        try:
            return datetime.fromisoformat(date_header.replace("Z", "+00:00"))
        except ValueError:
            pass
    timestamp = fields.get("timestamp")
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)
    except ValueError:
        return None
