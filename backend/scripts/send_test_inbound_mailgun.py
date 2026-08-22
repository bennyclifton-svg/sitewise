"""POST a signed Mailgun-shaped inbound payload to the local API."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import time
from urllib.request import Request, urlopen

from app.config import settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="Existing project slug, e.g. wianamatta-avenue")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/internal/email/inbound/mailgun",
    )
    args = parser.parse_args()
    key = settings.mailgun_inbound_signing_key
    if not key:
        raise SystemExit("MAILGUN_INBOUND_SIGNING_KEY is not set. Restart uvicorn after editing .env")
    timestamp = str(int(time.time()))
    token = "local-test"
    signature = hmac.new(
        key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    alias = f"{args.slug.strip().lower()}@{settings.email_inbound_domain}"
    boundary = "----sitewiseLocalInbound"
    fields = {
        "from": "you@example.com",
        "recipient": alias,
        "To": alias,
        "subject": "Local inbound test",
        "body-plain": "This is a local Mailgun webhook test.",
        "timestamp": timestamp,
        "token": token,
        "signature": signature,
        "Message-Id": f"<local-test-{timestamp}@sitewise.au>",
    }
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )
    parts.append(f"--{boundary}--\r\n")
    body = "".join(parts).encode("utf-8")
    request = Request(
        args.url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    print(f"posting {alias} (domain={settings.email_inbound_domain})")
    try:
        with urlopen(request, timeout=30) as response:
            print(response.status, response.read().decode("utf-8"))
            return
    except Exception as exc:
        detail = getattr(exc, "read", lambda: b"")()
        print(exc)
        if detail:
            print(detail.decode("utf-8", errors="replace"))
    probe = Request(args.url, data=b"probe=1", method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urlopen(probe, timeout=10) as response:
            print("unsigned probe", response.status)
    except Exception as exc:
        body = getattr(exc, "read", lambda: b"")()
        print("unsigned probe", exc)
        if body:
            print(body.decode("utf-8", errors="replace"))
        print(
            "404 here usually means the running uvicorn has no "
            "MAILGUN_INBOUND_SIGNING_KEY. Stop it with Ctrl+C and start it again."
        )


if __name__ == "__main__":
    main()
