from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import unquote_plus, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "connection_string",
        "cookie",
        "credentials",
        "database_url",
        "dsn",
        "headers",
        "id_token",
        "mcp_token",
        "password",
        "private_key",
        "proxy_authorization",
        "refresh_token",
        "request_headers",
        "response_headers",
        "secret",
        "set_cookie",
        "sig",
        "signature",
        "signed_url",
        "stripe_secret_key",
        "supabase_anon_key",
        "supabase_service_role_key",
        "token",
        "x_amz_signature",
    }
)
_SENSITIVE_KEY_SUFFIXES = (
    "_access_token",
    "_api_key",
    "_authorization",
    "_client_secret",
    "_cookie",
    "_database_url",
    "_dsn",
    "_headers",
    "_id_token",
    "_mcp_token",
    "_password",
    "_private_key",
    "_refresh_token",
    "_secret",
    "_signature",
    "_signed_url",
    "_token",
)
_AUTH_SCHEME_RE = re.compile(
    r"(?i)\b(Bearer|Basic)(\s+)(?!\[REDACTED\])[^\s,;]+"
)
_COOKIE_HEADER_RE = re.compile(r"(?im)\b(Set-Cookie|Cookie)\s*:\s*[^\r\n]*")
_ASSIGNMENT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9_.-])"
    r"(?P<prefix>['\"]?(?P<key>"
    r"(?:(?:[A-Za-z_][A-Za-z0-9_.-]*?)?(?:"
    r"access[_-]?token|api[_-]?key|authorization|client[_-]?secret|cookie|"
    r"database[_-]?url|dsn|headers|id[_-]?token|mcp[_-]?token|password|"
    r"private[_-]?key|refresh[_-]?token|secret|sig(?:nature)?|signed[_-]?url|token|"
    r"service[_-]?role[_-]?key|stripe[_-]?secret[_-]?key)"
    r"|credentials|connection[_-]?string|proxy[_-]?authorization|set[_-]?cookie)"
    r")['\"]?\s*[:=]\s*)"
    r"(?!\[REDACTED\])(?P<value>['\"][^'\"]*['\"]|[^\s,;{}&\]]+)"
)
_URL_RE = re.compile(
    r"(?i)\b(?:https?|postgres(?:ql)?(?:\+[a-z0-9]+)?|redis(?:\+[a-z0-9]+)?)"
    r"://[^\s<>\"']+"
)
_QUERY_PARAMETER_RE = re.compile(
    r"(?i)(?P<prefix>[?&](?P<key>[A-Za-z0-9_.%+-]+)=)"
    r"(?P<value>[^&#\s\"']*)"
)
_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "code",
        "credential",
        "key",
        "password",
        "refresh_token",
        "secret",
        "sig",
        "signature",
        "token",
        "x_amz_credential",
        "x_amz_security_token",
        "x_amz_signature",
    }
)


def _normalized_key(value: str) -> str:
    snake_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return re.sub(r"[^a-z0-9]+", "_", snake_case.lower()).strip("_")


def is_sensitive_key(value: str) -> bool:
    normalized = _normalized_key(value)
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        _SENSITIVE_KEY_SUFFIXES
    )


def _redact_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        netloc = parsed.netloc
        if "@" in netloc:
            netloc = f"{REDACTED}@{netloc.rsplit('@', maxsplit=1)[1]}"

        query_parts: list[str] = []
        for part in parsed.query.split("&"):
            key, separator, value = part.partition("=")
            if separator and _normalized_key(unquote_plus(key)) in _SENSITIVE_QUERY_KEYS:
                value = REDACTED
            query_parts.append(f"{key}{separator}{value}")

        return urlunsplit(
            (parsed.scheme, netloc, parsed.path, "&".join(query_parts), parsed.fragment)
        )
    except ValueError:
        # Malformed URLs are untrusted data. Returning a fixed replacement is
        # safer than allowing parser diagnostics to echo credentials.
        return REDACTED


def _redact_urls(value: str) -> str:
    return _URL_RE.sub(lambda match: _redact_url(match.group(0)), value)


def _redact_query_parameter(match: re.Match[str]) -> str:
    key = _normalized_key(unquote_plus(match.group("key")))
    if key not in _SENSITIVE_QUERY_KEYS:
        return match.group(0)
    return f"{match.group('prefix')}{REDACTED}"


def _redact_assignment(match: re.Match[str]) -> str:
    if not is_sensitive_key(match.group("key")):
        return match.group(0)
    return f"{match.group('prefix')}{REDACTED}"


class RecursiveLogRedactor:
    """Structlog processor that removes credentials from nested event data."""

    def __init__(self, *, secret_literals: Iterable[str] = ()) -> None:
        self._secret_literals = tuple(
            sorted(
                {value for value in secret_literals if len(value) >= 8},
                key=len,
                reverse=True,
            )
        )
        self.failure_count = 0

    def redact_value(self, value: Any) -> Any:
        """Redact one value for callers that run before structlog processors."""

        return self._redact(value)

    def __call__(
        self,
        _logger: Any,
        _method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return self._redact(event_dict)
        except Exception:
            self.failure_count += 1
            return {
                "event": "log_redaction_failed",
                "redaction_failure": True,
                "redaction_failure_count": self.failure_count,
            }

    def _redact(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                self._redact(key) if isinstance(key, str) else key: (
                    REDACTED
                    if isinstance(key, str) and is_sensitive_key(key)
                    else self._redact(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact(item) for item in value)
        if isinstance(value, set):
            return {self._redact(item) for item in value}
        if isinstance(value, frozenset):
            return frozenset(self._redact(item) for item in value)
        if isinstance(value, str):
            for secret in self._secret_literals:
                value = value.replace(secret, REDACTED)
            value = _AUTH_SCHEME_RE.sub(r"\1\2" + REDACTED, value)
            value = _COOKIE_HEADER_RE.sub(
                lambda match: f"{match.group(1)}: {REDACTED}", value
            )
            value = _QUERY_PARAMETER_RE.sub(_redact_query_parameter, value)
            value = _ASSIGNMENT_RE.sub(_redact_assignment, value)
            value = _redact_urls(value)
            return value
        return value


class RedactingLogFilter(logging.Filter):
    """Sanitize stdlib message arguments before ``LogRecord.getMessage``."""

    def __init__(self, redactor: RecursiveLogRedactor) -> None:
        super().__init__()
        self._redactor = redactor

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if (
                isinstance(record.msg, Mapping)
                and "_logger" in record.__dict__
                and "_name" in record.__dict__
            ):
                record.msg = self._redactor.redact_value(record.msg)
            else:
                record.msg = self._redactor.redact_value(record.getMessage())
            record.args = ()
        except Exception:
            self._redactor.failure_count += 1
            record.msg = "log_redaction_failed"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True
