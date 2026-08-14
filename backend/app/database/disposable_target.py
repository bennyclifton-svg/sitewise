from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from ipaddress import IPv4Network, IPv6Network, ip_address
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


_ALLOWED_NETWORKS = (
    IPv4Network("127.0.0.0/8"),
    IPv6Network("::1/128"),
)


@dataclass(frozen=True, slots=True)
class DisposableDatabaseTarget:
    host: str
    port: int
    database: str

    @property
    def endpoint(self) -> tuple[str, int]:
        return self.host, self.port


def authorize_database_connection(
    target: DisposableDatabaseTarget,
    address: object,
) -> bool:
    """Authorize only the parsed literal host and explicit port."""

    if not isinstance(address, tuple) or len(address) < 2:
        return False
    return address[0] == target.host and address[1] == target.port


def authorize_database_operation(
    target: DisposableDatabaseTarget,
    operation: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> bool:
    """Authorize resolver and connection calls for one literal endpoint only."""

    if operation in {"socket.getaddrinfo", "socket.create_connection"}:
        if len(args) >= 2:
            address: object = (args[0], args[1])
        elif args:
            address = args[0]
        else:
            address = kwargs.get("address")
        return authorize_database_connection(target, address)
    if operation in {"socket.socket.connect", "socket.socket.connect_ex"}:
        address = args[-1] if args else kwargs.get("address")
        return authorize_database_connection(target, address)
    return False


def parse_disposable_database_target(value: str) -> DisposableDatabaseTarget:
    """Parse a test target without retaining credentials or the original URL."""

    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("TEST_DATABASE_URL must use a PostgreSQL scheme")
    if parsed.query or parsed.fragment:
        raise ValueError(
            "TEST_DATABASE_URL must not include query parameters or fragments"
        )
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("TEST_DATABASE_URL must include an explicit host and port")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        raise ValueError("TEST_DATABASE_URL host must be a literal loopback address") from None
    if not any(address in network for network in _ALLOWED_NETWORKS):
        raise ValueError("TEST_DATABASE_URL host must be a literal loopback address")
    database = unquote(parsed.path.removeprefix("/"))
    if not database or "/" in database:
        raise ValueError("TEST_DATABASE_URL must identify one database")
    return DisposableDatabaseTarget(
        host=parsed.hostname,
        port=parsed.port,
        database=database,
    )


def require_test_environment_marker(connection: Any) -> None:
    """Fail closed unless the connected database identifies itself as test."""

    try:
        marker = connection.exec_driver_sql(
            "SELECT environment FROM clerk_test_environment WHERE id = 1"
        ).scalar_one_or_none()
    except Exception:
        raise RuntimeError(
            "disposable database environment marker could not be verified"
        ) from None
    if marker is None:
        raise RuntimeError("disposable database environment marker is missing")
    if marker != "test":
        raise RuntimeError("disposable database environment marker must equal 'test'")


def migration_database_url(
    *,
    application_url: str,
    test_url: str | None,
    database_integration: bool,
) -> str:
    """Select the migration URL without ever falling back in the test lane."""

    if database_integration:
        if not test_url:
            raise ValueError("TEST_DATABASE_URL is required for database migrations")
        parse_disposable_database_target(test_url)
        return _psycopg_url(test_url, sslmode="disable")
    return _psycopg_url(application_url, sslmode="require")


def _psycopg_url(value: str, *, sslmode: str) -> str:
    parsed = urlsplit(value)
    scheme = parsed.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+psycopg"
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("sslmode", sslmode)
    return urlunsplit(
        (scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def main() -> int:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        print(
            "database-target-rejected: TEST_DATABASE_URL is required",
            file=sys.stderr,
        )
        return 2
    try:
        target = parse_disposable_database_target(value)
    except ValueError as exc:
        reason = str(exc).removeprefix("TEST_DATABASE_URL ")
        print(f"database-target-rejected: {reason}", file=sys.stderr)
        return 2
    print(
        "database-target-ok "
        f"host={target.host} port={target.port} database={target.database}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
