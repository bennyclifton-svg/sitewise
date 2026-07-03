"""Short-lived HMAC turn tokens binding a Hermes turn to (user, project)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from app.config import settings


class TurnTokenError(Exception):
    pass


class TurnTokenConfigurationError(TurnTokenError):
    pass


@dataclass(frozen=True, slots=True)
class TurnClaims:
    user_id: uuid.UUID
    project_id: uuid.UUID
    expires_at: float


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: bytes, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), body, hashlib.sha256).digest())


def _resolve_secret(secret: str | None) -> str:
    value = secret if secret is not None else settings.agent_turn_token_secret
    if not value:
        raise TurnTokenConfigurationError("turn token secret is not configured")
    return value


def mint_turn_token(
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    ttl_seconds: int = 900,
    secret: str | None = None,
    now: float | None = None,
) -> str:
    secret = _resolve_secret(secret)
    now = time.time() if now is None else now
    body = json.dumps(
        {"uid": str(user_id), "pid": str(project_id), "exp": now + ttl_seconds},
        separators=(",", ":"),
    ).encode()
    return f"{_b64(body)}.{_sign(body, secret)}"


def verify_turn_token(
    token: str,
    *,
    secret: str | None = None,
    now: float | None = None,
) -> TurnClaims:
    secret = _resolve_secret(secret)
    now = time.time() if now is None else now
    try:
        body_b64, sig = token.rsplit(".", 1)
        body = _unb64(body_b64)
    except Exception as exc:
        raise TurnTokenError("malformed token") from exc
    if not hmac.compare_digest(_sign(body, secret), sig):
        raise TurnTokenError("bad signature")
    payload = json.loads(body)
    if payload["exp"] <= now:
        raise TurnTokenError("expired")
    return TurnClaims(
        user_id=uuid.UUID(payload["uid"]),
        project_id=uuid.UUID(payload["pid"]),
        expires_at=payload["exp"],
    )
