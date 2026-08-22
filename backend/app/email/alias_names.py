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
