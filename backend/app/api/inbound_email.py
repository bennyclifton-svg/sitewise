"""Unauthenticated inbound alias webhooks. HMAC or Mailgun signature; 404 if unset."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.email.inbound import (
    INBOUND_EMAIL_PATH,
    INBOUND_SIGNATURE_HEADER,
    InboundAliasUnresolved,
    ingest_inbound_payload,
    inbound_request_exceeds_limit,
)
from app.email.mailgun import (
    MAILGUN_INBOUND_PATH,
    inbound_payload_from_mailgun,
    mailgun_signature_valid,
    mailgun_timestamp_stale,
)
from app.inbox.service import InboxUploadValidationError

router = APIRouter(tags=["inbound-email"])
INBOUND_EMAIL_PATHS = frozenset({INBOUND_EMAIL_PATH, MAILGUN_INBOUND_PATH})


def _payload_too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail="Inbound email payload exceeds size limit",
    )


def verify_inbound_signature(body: bytes, signature: str | None) -> None:
    secret = settings.email_inbound_webhook_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound signature",
        )
    provided = signature.removeprefix("sha256=")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound signature",
        )


@router.post(INBOUND_EMAIL_PATH)
async def post_inbound_email(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    content_length = request.headers.get("content-length")
    if inbound_request_exceeds_limit(content_length=content_length, body_len=0):
        raise _payload_too_large()
    body = await request.body()
    if inbound_request_exceeds_limit(
        content_length=content_length, body_len=len(body)
    ):
        raise _payload_too_large()
    verify_inbound_signature(body, request.headers.get(INBOUND_SIGNATURE_HEADER))
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )
    return await _ingest_or_raise(session, payload)


@router.post(MAILGUN_INBOUND_PATH)
async def post_mailgun_inbound_email(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    signing_key = settings.mailgun_inbound_signing_key
    if not signing_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    content_length = request.headers.get("content-length")
    if inbound_request_exceeds_limit(content_length=content_length, body_len=0):
        raise _payload_too_large()
    form = await request.form()
    timestamp = _form_str(form, "timestamp")
    token = _form_str(form, "token")
    signature = _form_str(form, "signature")
    if mailgun_timestamp_stale(timestamp, now=int(time.time())):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound signature",
        )
    if not mailgun_signature_valid(
        signing_key=signing_key,
        timestamp=timestamp,
        token=token,
        signature=signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inbound signature",
        )
    fields = {
        key: value
        for key, value in form.multi_items()
        if isinstance(value, str)
    }
    attachments: list[tuple[str, bytes, str | None]] = []
    for key, value in form.multi_items():
        if not key.startswith("attachment-") or isinstance(value, str):
            continue
        content = await value.read()
        attachments.append(
            (value.filename or key, content, value.content_type)
        )
    payload = inbound_payload_from_mailgun(fields=fields, attachments=attachments)
    return await _ingest_or_raise(session, payload)


def _form_str(form, key: str) -> str:
    value = form.get(key)
    return value if isinstance(value, str) else ""


async def _ingest_or_raise(session: AsyncSession, payload: dict) -> dict[str, str]:
    try:
        return await ingest_inbound_payload(session, payload)
    except InboundAliasUnresolved as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        ) from exc
    except (ValidationError, ValueError, InboxUploadValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


async def cap_inbound_email_body(request: Request, call_next):
    if request.url.path in INBOUND_EMAIL_PATHS and request.method == "POST":
        content_length = request.headers.get("content-length")
        if inbound_request_exceeds_limit(content_length=content_length, body_len=0):
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Inbound email payload exceeds size limit"},
            )
    return await call_next(request)
