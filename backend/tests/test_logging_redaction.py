from __future__ import annotations

import io
import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Any

import structlog

from app import logging as app_logging
from app.log_redaction import REDACTED, RecursiveLogRedactor


def _canary(label: str) -> str:
    return f"ch03-{label}-" + ("x" * 24)


class _ExplodingMapping(Mapping[str, Any]):
    def __getitem__(self, key: str) -> Any:
        raise RuntimeError("mapping cannot be inspected")

    def __iter__(self):
        raise RuntimeError("mapping cannot be inspected")

    def __len__(self) -> int:
        return 1


@contextmanager
def _capture_configured_logging() -> Iterator[io.StringIO]:
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    previous_structlog_config = structlog.get_config().copy()
    previous_configured = app_logging._configured
    uvicorn_loggers = {
        name: logging.getLogger(name)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
    }
    previous_uvicorn_state = {
        name: (logger.handlers[:], logger.propagate, logger.disabled)
        for name, logger in uvicorn_loggers.items()
    }
    stream = io.StringIO()

    try:
        app_logging._configured = False
        with redirect_stdout(stream), redirect_stderr(stream):
            app_logging.configure_logging()
            yield stream
    finally:
        root.handlers.clear()
        root.handlers.extend(previous_handlers)
        root.setLevel(previous_level)
        structlog.configure(**previous_structlog_config)
        app_logging._configured = previous_configured
        for name, logger in uvicorn_loggers.items():
            handlers, propagate, disabled = previous_uvicorn_state[name]
            logger.handlers.clear()
            logger.handlers.extend(handlers)
            logger.propagate = propagate
            logger.disabled = disabled


def test_redacts_sensitive_keys_recursively_and_preserves_correlation() -> None:
    redactor = RecursiveLogRedactor()
    project_id = "11111111-2222-3333-4444-555555555555"
    event = {
        "password": _canary("password"),
        "nested": {
            "authorization": f"Bearer {_canary('bearer')}",
            "items": [
                {"access_token": _canary("access-token")},
                {"project_id": project_id, "status": "queued"},
            ],
        },
    }

    redacted = redactor(None, "info", event)

    assert redacted == {
        "password": REDACTED,
        "nested": {
            "authorization": REDACTED,
            "items": [
                {"access_token": REDACTED},
                {"project_id": project_id, "status": "queued"},
            ],
        },
    }


def test_redacts_provider_secret_keys_but_keeps_safe_storage_key() -> None:
    redactor = RecursiveLogRedactor()
    event = {
        "openai_api_key": _canary("openai-key"),
        "custom_access_token": _canary("custom-token"),
        "request_headers": {"X-Correlation-ID": "request-123"},
        "storage_key": "project/files/report.pdf",
    }

    redacted = redactor(None, "info", event)

    assert redacted == {
        "openai_api_key": REDACTED,
        "custom_access_token": REDACTED,
        "request_headers": REDACTED,
        "storage_key": "project/files/report.pdf",
    }


def test_redacts_credentials_from_formatted_exception_text() -> None:
    redactor = RecursiveLogRedactor()
    event = {
        "exception": (
            f"RuntimeError: upstream rejected Bearer {_canary('exception-bearer')}\n"
            f"Cookie: session={_canary('exception-cookie')}"
        )
    }

    redacted = redactor(None, "error", event)

    assert redacted["exception"].startswith("RuntimeError: upstream rejected Bearer ")
    assert redacted["exception"].endswith(f"Cookie: {REDACTED}")
    assert _canary("exception-bearer") not in redacted["exception"]
    assert _canary("exception-cookie") not in redacted["exception"]


def test_redacts_dynamic_token_assignments_and_basic_authorization() -> None:
    redactor = RecursiveLogRedactor()
    assignment_secret = _canary("assignment")
    basic_secret = _canary("basic")
    camel_secret = _canary("camel")
    event = {
        "event": (
            f"CLERK_MCP_TOKEN={assignment_secret} safe_field=kept "
            f"Authorization: Basic {basic_secret} "
            f"payload={{'accessToken': '{camel_secret}', 'count': 2}} "
            f"path=/callback?agent_turn_token={assignment_secret}&page=2"
        ),
        "clientSecret": camel_secret,
    }

    redacted = redactor(None, "error", event)
    rendered = str(redacted)

    assert assignment_secret not in rendered
    assert basic_secret not in rendered
    assert camel_secret not in rendered
    assert "safe_field=kept" in redacted["event"]
    assert "'count': 2" in redacted["event"]
    assert "page=2" in redacted["event"]
    assert redacted["clientSecret"] == REDACTED


def test_redacts_relative_signed_query_parameters_and_structured_signatures() -> None:
    signature = _canary("relative-signature")
    short_signature = _canary("relative-sig")
    authorization_code = _canary("relative-code")
    storage_credential = _canary("relative-credential")
    event = {
        "event": (
            f"GET /download?X-Amz-Signature={signature}&sig={short_signature}"
            f"&code={authorization_code}&X-Amz-Credential={storage_credential}"
            "&download=1"
        ),
        "signature": signature,
        "customSignature": short_signature,
        "code": "safe-business-code",
    }

    redacted = RecursiveLogRedactor()(None, "info", event)

    assert signature not in str(redacted)
    assert short_signature not in str(redacted)
    assert authorization_code not in str(redacted)
    assert storage_credential not in str(redacted)
    assert "download=1" in redacted["event"]
    assert redacted["signature"] == REDACTED
    assert redacted["customSignature"] == REDACTED
    assert redacted["code"] == "safe-business-code"


def test_redacts_url_userinfo_and_signed_query_parameters() -> None:
    redactor = RecursiveLogRedactor()
    username = _canary("url-user")
    password = _canary("url-password")
    token = _canary("query-token")
    signature = _canary("query-signature")
    event = {
        "event": (
            "provider failed for "
            f"https://{username}:{password}@storage.example.test/files/report.pdf"
            f"?download=1&token={token}&X-Amz-Signature={signature}"
        )
    }

    redacted = redactor(None, "error", event)["event"]

    assert "https://[REDACTED]@storage.example.test/files/report.pdf" in redacted
    assert "download=1" in redacted
    assert "token=" in redacted
    assert "X-Amz-Signature=" in redacted
    assert username not in redacted
    assert password not in redacted
    assert token not in redacted
    assert signature not in redacted


def test_redacts_configured_secret_literals_of_at_least_eight_characters() -> None:
    configured_secret = _canary("configured-secret")
    short_value = "short7"
    redactor = RecursiveLogRedactor(
        secret_literals=[configured_secret, short_value]
    )
    event = {
        "event": f"provider rejected {configured_secret}",
        "nested": [f"retry used {configured_secret}", f"safe {short_value}"],
    }

    redacted = redactor(None, "error", event)

    assert configured_secret not in str(redacted)
    assert redacted["event"] == f"provider rejected {REDACTED}"
    assert redacted["nested"][1] == f"safe {short_value}"


def test_redacts_configured_secret_when_used_as_mapping_key() -> None:
    configured_secret = _canary("configured-mapping-key")
    redactor = RecursiveLogRedactor(secret_literals=[configured_secret])

    redacted = redactor(None, "error", {configured_secret: "provider response"})

    assert configured_secret not in str(redacted)
    assert redacted == {REDACTED: "provider response"}


def test_configured_secret_extraction_uses_shared_sensitive_key_policy(
    monkeypatch,
) -> None:
    future_secret = _canary("future-setting")
    monkeypatch.setattr(
        type(app_logging.settings),
        "model_dump",
        lambda self: {
            "futureProviderToken": future_secret,
            "safe_label": future_secret,
        },
    )

    assert app_logging._configured_secret_literals() == [future_secret]


def test_configured_url_literal_is_fully_redacted() -> None:
    configured_url = (
        "postgresql://configured-user:configured-password@database.example.test/app"
    )
    redactor = RecursiveLogRedactor(secret_literals=[configured_url])

    redacted = redactor(
        None,
        "error",
        {"event": f"database unavailable at {configured_url}"},
    )

    assert redacted["event"] == f"database unavailable at {REDACTED}"
    assert "configured-user" not in redacted["event"]
    assert "database.example.test" not in redacted["event"]


def test_redaction_failure_fails_closed_and_increments_counter() -> None:
    redactor = RecursiveLogRedactor()

    redacted = redactor(
        None,
        "error",
        {"event": "provider failure", "unsafe": _ExplodingMapping()},
    )

    assert redacted == {
        "event": "log_redaction_failed",
        "redaction_failure": True,
        "redaction_failure_count": 1,
    }
    assert redactor.failure_count == 1


def test_configured_structlog_and_stdlib_logs_share_exception_redaction(
    monkeypatch,
) -> None:
    configured_secret = _canary("configured-logger-secret")
    structlog_secret = _canary("structlog-bearer")
    stdlib_secret = _canary("stdlib-cookie")
    stdlib_field_secret = _canary("stdlib-password")
    stdlib_second_secret = _canary("stdlib-second-password")
    stdlib_extra_secret = _canary("stdlib-extra-password")
    relative_query_secret = _canary("relative-query-token")
    exception_secret = _canary("structlog-exception")
    service_role_secret = _canary("service-role")
    anon_key_secret = _canary("anon-key")
    stripe_secret = _canary("stripe-secret")
    project_id = "11111111-2222-3333-4444-555555555555"
    monkeypatch.setattr(app_logging.settings, "openai_api_key", configured_secret)
    monkeypatch.setattr(
        app_logging.settings, "supabase_service_role_key", service_role_secret
    )
    monkeypatch.setattr(app_logging.settings, "supabase_anon_key", anon_key_secret)
    monkeypatch.setattr(app_logging.settings, "stripe_secret_key", stripe_secret)

    with _capture_configured_logging() as stream:
        structlog.get_logger("ch03.structlog").error(
            "structured_provider_failure",
            authorization=f"Bearer {structlog_secret}",
            configured_value=f"prefix:{configured_secret}",
            service_role_value=f"prefix:{service_role_secret}",
            anon_key_value=f"prefix:{anon_key_secret}",
            project_id=project_id,
        )
        try:
            raise RuntimeError(f"Authorization: Bearer {exception_secret}")
        except RuntimeError as error:
            structlog.get_logger("ch03.structlog.exception").exception(
                "structured_exception",
                exc_info=error,
                project_id=project_id,
            )
        try:
            raise RuntimeError(f"Cookie: session={stdlib_secret}")
        except RuntimeError:
            logging.getLogger("ch03.stdlib").exception(
                "stdlib_provider_failure project_id=%s configured=%s",
                project_id,
                configured_secret,
                extra={"stripe_result": f"prefix:{stripe_secret}"},
            )
        logging.getLogger("ch03.stdlib.fields").error(
            "stdlib_fields=%s second=%s",
            {"password": stdlib_field_secret},
            {"password": stdlib_second_secret},
            extra={"project_id": project_id, "password": stdlib_extra_secret},
        )
        logging.getLogger("ch03.uvicorn-style").info(
            '127.0.0.1 - "GET /callback?token=%s&page=2 HTTP/1.1" 200',
            relative_query_secret,
        )

    rendered = stream.getvalue()
    assert "structured_provider_failure" in rendered
    assert "stdlib_provider_failure" in rendered
    assert "RuntimeError" in rendered
    assert project_id in rendered
    assert structlog_secret not in rendered
    assert stdlib_secret not in rendered
    assert stdlib_field_secret not in rendered
    assert stdlib_second_secret not in rendered
    assert stdlib_extra_secret not in rendered
    assert relative_query_secret not in rendered
    assert exception_secret not in rendered
    assert configured_secret not in rendered
    assert service_role_secret not in rendered
    assert anon_key_secret not in rendered
    assert stripe_secret not in rendered
    assert "page=2" in rendered
    assert "GET /callback" in rendered
    assert "Logging error" not in rendered
    assert REDACTED in rendered


def test_configured_logging_disables_uvicorn_access_logger() -> None:
    with _capture_configured_logging():
        assert logging.getLogger("uvicorn.access").disabled is True
