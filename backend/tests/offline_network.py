import functools
import os
import socket
import tempfile
import threading
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

from app.database.disposable_target import (
    DisposableDatabaseTarget,
    authorize_database_operation,
    parse_disposable_database_target,
)


_STARTUP_NETWORK_OPT_IN = os.environ.get("CLERK_TEST_ALLOW_NETWORK") == "1"
_STARTUP_DATABASE_OPT_IN = os.environ.get("DATABASE_INTEGRATION_TESTS") == "1"
_startup_test_database_url = os.environ.get("TEST_DATABASE_URL")
if _STARTUP_DATABASE_OPT_IN:
    if not _startup_test_database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required for database integration tests"
        )
    try:
        _STARTUP_DATABASE_TARGET = parse_disposable_database_target(
            _startup_test_database_url
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from None
else:
    _STARTUP_DATABASE_TARGET = None
_INTEGRATION_OVERRIDE_NAMES = (
    "TENDER_LIVE_EVAL",
    "TENDER_PERF_WRITE_REPORT",
    "TENDER_ENFORCE_90S",
)
_STARTUP_INTEGRATION_OVERRIDES = {
    name: os.environ.get(name) for name in _INTEGRATION_OVERRIDE_NAMES
}
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Settings loads backend/.env. Assignment before any app import prevents that
# ignored file or the parent shell from supplying credentials to ordinary tests.
TEST_ENV_SENTINELS = MappingProxyType(
    {
        "DEPLOYMENT_ENVIRONMENT": "test",
        "BUILD_SHA": "pytest-offline-sentinel",
        "DATABASE_URL": (
            "postgresql://clerk_test:clerk_test@127.0.0.1:9/"
            "application_database_must_not_be_contacted"
        ),
        "PGHOST": "127.0.0.1",
        "PGPORT": "9",
        "PGDATABASE": "application_database_must_not_be_contacted",
        "PGUSER": "clerk_test",
        "PGPASSWORD": "test-password-must-not-authenticate",
        "PGSSLMODE": "disable",
        "TEST_DATABASE_URL": (
            "postgresql://clerk_test:clerk_test@127.0.0.1:9/"
            "test_database_must_not_be_contacted"
        ),
        "DATABASE_INTEGRATION_TESTS": "0",
        "ALLOW_DESTRUCTIVE_TEST_DATABASE": "0",
        "SUPABASE_URL": "https://clerk-pytest.invalid",
        "SUPABASE_ANON_KEY": "test-anon-key-must-not-authenticate",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key-must-not-authenticate",
        "SUPABASE_STORAGE_BUCKET": "test-project-files",
        "OPENAI_API_KEY": "test-openai-key-must-not-authenticate",
        "XAI_API_KEY": "test-xai-key-must-not-authenticate",
        "PI_MODEL_PROVIDER": "openai",
        "PI_MODEL": "gpt-5.6-luna",
        "PI_MODEL_OPTIONS": "openai:gpt-5.6-luna:Fast,xai:grok-4.6:Thorough",
        "OPENAI_ORG_ID": "test-openai-org",
        "OPENAI_PROJECT_ID": "test-openai-project",
        "OPENAI_BASE_URL": "https://openai-pytest.invalid/v1",
        "PUBLIC_APP_URL": "http://testserver",
        "ALLOWED_ORIGINS": "http://testserver,http://localhost:5173",
        "DATA_DIR": str(_REPO_ROOT / "data"),
        "BILLING_PROVIDER": "none",
        "STRIPE_SECRET_KEY": "test-stripe-key-must-not-authenticate",
        "STRIPE_WEBHOOK_SECRET": "test-stripe-webhook-must-not-authenticate",
        "STRIPE_PRICE_ID": "test-stripe-price",
        "AGENT_RUNTIME_ENABLED": "false",
        "AGENT_PLATFORM_API_KEY": "test-agent-platform-key-must-not-authenticate",
        "AGENT_TURN_TOKEN_SECRET": "test-turn-token-secret-000000000000000000000000",
        "PI_BINARY_PATH": "__clerk_pytest_pi_must_not_execute__",
        "PI_MCP_ADAPTER_PATH": "__clerk_pytest_adapter_must_not_execute__",
        "AGENT_MCP_URL": "http://127.0.0.1:9/mcp-must-not-be-contacted",
        "AGENT_WORKSPACE_ROOT": str(
            Path(tempfile.gettempdir()) / "clerk-pytest-agent-workspaces"
        ),
        "AGENT_WEB_RESEARCH_ENABLED": "false",
        "WEB_SEARCH_PROVIDER": "nsw_legislation",
        "BRAVE_SEARCH_API_KEY": "test-brave-key-must-not-authenticate",
        "TENDER_ODL_HYBRID_ENABLED": "false",
        "TENDER_ODL_HYBRID_URL": "http://127.0.0.1:9/odl-must-not-be-contacted",
        "TENDER_WORKER_INPROC_ENABLED": "false",
        "WORKFLOW_WORKER_INPROC_ENABLED": "false",
        "AGENT_EXECUTION_SCOPE": "test-agent",
        "WORKFLOW_QUEUE_SCOPE": "test-workflow",
        "TENDER_QUEUE_SCOPE": "test-tender",
        "STORAGE_CLEANUP_QUEUE_SCOPE": "test-storage-cleanup",
        "PARSER_QUEUE_SCOPE": "test-parser",
        "TENDER_LIVE_EVAL": "0",
        "TENDER_PERF_WRITE_REPORT": "0",
        "TENDER_ENFORCE_90S": "0",
        "CLERK_TEST_ALLOW_NETWORK": "0",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "clerk-pytest-no-proxy.invalid",
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "all_proxy": "http://127.0.0.1:9",
        "no_proxy": "clerk-pytest-no-proxy.invalid",
    }
)
os.environ.update(TEST_ENV_SENTINELS)

if _STARTUP_DATABASE_TARGET is not None:
    os.environ["DATABASE_INTEGRATION_TESTS"] = "1"
    os.environ["TEST_DATABASE_URL"] = _startup_test_database_url
del _startup_test_database_url

# A generic network opt-in never authorizes database access. Database tests use
# a separate marker and exact loopback endpoint; all other tests keep both
# database URLs and the destructive flag on unreachable sentinels.
if _STARTUP_NETWORK_OPT_IN:
    os.environ["CLERK_TEST_ALLOW_NETWORK"] = "1"
    for _name, _value in _STARTUP_INTEGRATION_OVERRIDES.items():
        if _value is not None:
            os.environ[_name] = _value


class OfflineNetworkBlocked(RuntimeError):
    """Raised when an offline test attempts DNS resolution or a connection."""


_NETWORK_ELIGIBLE_MARKERS = frozenset({"integration", "tender_eval"})


def network_access_permitted(marker_names: set[str], opt_in: str | None) -> bool:
    """Return true only for an eligible marker and the exact opt-in value."""

    return opt_in == "1" and bool(marker_names & _NETWORK_ELIGIBLE_MARKERS)


def startup_network_access_permitted(marker_names: set[str]) -> bool:
    """Evaluate markers against the immutable process-start opt-in decision."""

    opt_in = "1" if _STARTUP_NETWORK_OPT_IN else "0"
    return network_access_permitted(marker_names, opt_in)


def database_access_target(
    marker_names: set[str],
    opt_in: str | None,
    test_url: str | None,
) -> DisposableDatabaseTarget | None:
    """Return the one database endpoint authorized for this marked test."""

    if "database_integration" not in marker_names or opt_in != "1":
        return None
    if not test_url:
        raise ValueError("TEST_DATABASE_URL is required for database integration tests")
    return parse_disposable_database_target(test_url)


def startup_database_access_target(
    marker_names: set[str],
) -> DisposableDatabaseTarget | None:
    """Return immutable database authority only to its dedicated marker."""

    if "database_integration" not in marker_names:
        return None
    return _STARTUP_DATABASE_TARGET


@dataclass(frozen=True)
class _NetworkAuthorityLease:
    generation: object | None
    context_token: Token[object | None]


class _OfflineNetworkGuard:
    def __init__(self) -> None:
        self._installed = False
        self._internal = threading.local()
        self._authority_context: ContextVar[object | None] = ContextVar(
            "clerk_pytest_network_authority",
            default=None,
        )
        self._active_generation: object | None = None
        self._active_database_target: DisposableDatabaseTarget | None = None
        self._unrestricted_network = False
        self._protocol_active = False
        self._authority_lock = threading.Lock()

    @property
    def allowed(self) -> bool:
        generation = self._authority_context.get()
        with self._authority_lock:
            return (
                generation is not None
                and generation is self._active_generation
                and self._unrestricted_network
            )

    @property
    def database_target(self) -> DisposableDatabaseTarget | None:
        generation = self._authority_context.get()
        with self._authority_lock:
            if generation is None or generation is not self._active_generation:
                return None
            return self._active_database_target

    def begin_test(
        self,
        *,
        allowed: bool,
        database_target: DisposableDatabaseTarget | None = None,
    ) -> _NetworkAuthorityLease:
        """Open one test protocol and bind any authority to its context."""

        with self._authority_lock:
            if self._protocol_active:
                raise RuntimeError(
                    "offline network guard does not support same-process "
                    "parallel pytest protocols"
                )
            self._protocol_active = True
            generation = object() if allowed or database_target is not None else None
            self._active_generation = generation
            self._active_database_target = database_target
            self._unrestricted_network = allowed
        context_token = self._authority_context.set(generation)
        return _NetworkAuthorityLease(generation, context_token)

    def end_test(self, lease: _NetworkAuthorityLease) -> None:
        """Invalidate a protocol's authority before restoring its context."""

        with self._authority_lock:
            if (
                not self._protocol_active
                or lease.generation is not self._active_generation
            ):
                raise RuntimeError("offline network authority lease mismatch")
            self._active_generation = None
            self._active_database_target = None
            self._unrestricted_network = False
            self._protocol_active = False
        self._authority_context.reset(lease.context_token)

    def call(
        self,
        original: Callable[..., Any],
        *args: Any,
        allowed_for_test: bool | None = None,
        operation: str = "socket operation",
        **kwargs: Any,
    ) -> Any:
        if allowed_for_test is None:
            explicitly_allowed = self.allowed
            database_target = self.database_target
            if database_target is not None:
                explicitly_allowed = authorize_database_operation(
                    database_target,
                    operation,
                    args,
                    kwargs,
                )
        else:
            explicitly_allowed = allowed_for_test
        inside_socketpair = getattr(self._internal, "socketpair_depth", 0) > 0
        if not explicitly_allowed and not inside_socketpair:
            raise OfflineNetworkBlocked(f"offline pytest blocked {operation}")
        return original(*args, **kwargs)

    def install(self) -> None:
        if self._installed:
            return

        def guarded(
            operation: str, original: Callable[..., Any]
        ) -> Callable[..., Any]:
            @functools.wraps(original)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return self.call(
                    original,
                    *args,
                    operation=operation,
                    **kwargs,
                )

            return wrapper

        for name in (
            "getaddrinfo",
            "gethostbyname",
            "gethostbyname_ex",
            "gethostbyaddr",
            "getnameinfo",
            "create_connection",
        ):
            original = getattr(socket, name)
            setattr(socket, name, guarded(f"socket.{name}", original))

        for name in ("connect", "connect_ex", "sendto", "sendmsg"):
            original = getattr(socket.socket, name, None)
            if original is not None:
                setattr(
                    socket.socket,
                    name,
                    guarded(f"socket.socket.{name}", original),
                )

        original_socketpair = getattr(socket, "socketpair", None)
        if original_socketpair is not None:

            @functools.wraps(original_socketpair)
            def guarded_socketpair(*args: Any, **kwargs: Any) -> Any:
                depth = getattr(self._internal, "socketpair_depth", 0)
                self._internal.socketpair_depth = depth + 1
                try:
                    return original_socketpair(*args, **kwargs)
                finally:
                    self._internal.socketpair_depth = depth

            socket.socketpair = guarded_socketpair

        self._installed = True


OFFLINE_NETWORK_GUARD = _OfflineNetworkGuard()
OFFLINE_NETWORK_GUARD.install()
