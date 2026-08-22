"""Local-parts that must never resolve as a project inbound alias."""

from __future__ import annotations

RESERVED_INBOUND_LOCAL_PARTS = frozenset(
    {
        "abuse",
        "admin",
        "administrator",
        "billing",
        "contact",
        "email",
        "hello",
        "hostmaster",
        "info",
        "mail",
        "noreply",
        "no-reply",
        "postmaster",
        "root",
        "security",
        "support",
        "www",
    }
)


def is_reserved_inbound_local_part(local: str) -> bool:
    return local.strip().lower() in RESERVED_INBOUND_LOCAL_PARTS


def inbound_address_for_slug(slug: str) -> str | None:
    """The address to advertise for a project, or None if it cannot receive.

    This is the inverse of `project_code_from_alias`. Deriving the displayed
    address from the same setting the resolver reads is what stops the UI
    advertising an address that would 404 on arrival.
    """
    from app.config import settings

    code = slug.strip().lower()
    if not code or is_reserved_inbound_local_part(code):
        return None
    return f"{code}@{settings.email_inbound_domain}"
