from __future__ import annotations

import os
import subprocess
import sys

import pytest

from app.database.disposable_target import (
    authorize_database_connection,
    authorize_database_operation,
    migration_database_url,
    parse_disposable_database_target,
    require_test_environment_marker,
)
from tests import offline_network


def test_disposable_target_accepts_loopback_without_retaining_credentials() -> None:
    password = "ch08-database-password-must-not-be-rendered"

    target = parse_disposable_database_target(
        f"postgresql://clerk_test:{password}@127.0.0.1:55432/clerk_test"
    )

    assert target.host == "127.0.0.1"
    assert target.port == 55432
    assert target.database == "clerk_test"
    assert target.endpoint == ("127.0.0.1", 55432)
    assert password not in repr(target)


@pytest.mark.parametrize(
    "host",
    [
        "8.8.8.8",
        "0.0.0.0",
        "10.20.30.40",
        "172.20.30.40",
        "192.168.20.30",
        "[fc00::10]",
        "169.254.10.20",
        "database",
        "db.example.com",
        "aws-0-region.pooler.supabase.com",
    ],
)
def test_disposable_target_rejects_public_and_dns_hosts(host: str) -> None:
    password = "ch08-rejected-password-must-not-be-rendered"

    with pytest.raises(ValueError) as captured:
        parse_disposable_database_target(
            f"postgresql://clerk_test:{password}@{host}:5432/clerk_test"
        )

    assert password not in str(captured.value)


@pytest.mark.parametrize(
    "suffix",
    [
        "?host=10.20.30.40",
        "?hostaddr=10.20.30.40",
        "?service=production",
        "#connection-override",
    ],
)
def test_disposable_target_rejects_libpq_connection_overrides(suffix: str) -> None:
    password = "ch08-override-password-must-not-be-rendered"

    with pytest.raises(ValueError) as captured:
        parse_disposable_database_target(
            "postgresql://clerk_test:"
            f"{password}@127.0.0.1:55432/clerk_test{suffix}"
        )

    assert password not in str(captured.value)


def test_database_access_requires_dedicated_marker_and_exact_opt_in() -> None:
    test_url = "postgresql://clerk_test:password@127.0.0.1:55432/clerk_test"
    access_target = offline_network.database_access_target

    assert access_target(set(), "1", test_url) is None
    assert access_target({"integration"}, "1", test_url) is None
    assert access_target({"database_integration"}, None, test_url) is None
    assert access_target({"database_integration"}, "0", test_url) is None
    assert access_target({"database_integration"}, "true", test_url) is None
    assert access_target({"database_integration"}, " 1", test_url) is None

    target = access_target({"database_integration"}, "1", test_url)

    assert target is not None
    assert target.endpoint == ("127.0.0.1", 55432)


def test_dedicated_process_preserves_only_the_validated_test_target() -> None:
    password = "ch08-child-password-must-not-be-rendered"
    child_env = os.environ.copy()
    child_env.update(
        {
            "DATABASE_INTEGRATION_TESTS": "1",
            "TEST_DATABASE_URL": (
                f"postgresql://clerk_test:{password}@127.0.0.1:55432/clerk_test"
            ),
            "DATABASE_URL": "postgresql://production.example.invalid/live",
            "CLERK_TEST_ALLOW_NETWORK": "0",
        }
    )
    script = (
        "import os; import tests.offline_network as policy; "
        "target = policy.startup_database_access_target({'database_integration'}); "
        "assert target is not None; "
        "assert target.endpoint == ('127.0.0.1', 55432); "
        "assert target.database == 'clerk_test'; "
        "assert os.environ['DATABASE_INTEGRATION_TESTS'] == '1'; "
        "assert os.environ['TEST_DATABASE_URL'].endswith('/clerk_test'); "
        "assert 'production.example.invalid' not in os.environ['DATABASE_URL']; "
        "print('database-target-contained')"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        env=child_env,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "database-target-contained"
    assert password not in completed.stdout
    assert password not in completed.stderr


def test_dedicated_process_rejects_unsafe_target_before_collection() -> None:
    password = "ch08-public-password-must-not-be-rendered"
    child_env = os.environ.copy()
    child_env.update(
        {
            "DATABASE_INTEGRATION_TESTS": "1",
            "TEST_DATABASE_URL": (
                "postgresql://clerk_test:"
                f"{password}@aws-0-region.pooler.supabase.com:5432/postgres"
            ),
        }
    )

    completed = subprocess.run(
        [sys.executable, "-c", "import tests.offline_network"],
        capture_output=True,
        env=child_env,
        text=True,
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "literal loopback address" in rendered
    assert password not in rendered


def test_connection_authority_is_exactly_one_host_and_port() -> None:
    target = parse_disposable_database_target(
        "postgresql://clerk_test:password@127.0.0.1:55432/clerk_test"
    )

    assert authorize_database_connection(target, ("127.0.0.1", 55432)) is True
    assert authorize_database_connection(target, ("127.0.0.1", 5432)) is False
    assert authorize_database_connection(target, ("127.0.0.2", 55432)) is False
    assert authorize_database_connection(target, ("localhost", 55432)) is False


def test_database_dns_and_socket_authority_require_exact_literal_endpoint() -> None:
    target = parse_disposable_database_target(
        "postgresql://clerk_test:password@127.0.0.1:55432/clerk_test"
    )

    assert authorize_database_operation(
        target,
        "socket.getaddrinfo",
        ("127.0.0.1", 55432),
        {},
    ) is True
    assert authorize_database_operation(
        target,
        "socket.socket.connect",
        (object(), ("127.0.0.1", 55432)),
        {},
    ) is True
    assert authorize_database_operation(
        target,
        "socket.getaddrinfo",
        ("localhost", 55432),
        {},
    ) is False
    assert authorize_database_operation(
        target,
        "socket.getaddrinfo",
        ("127.0.0.1", 443),
        {},
    ) is False


@pytest.mark.database_integration
def test_database_marker_grants_only_the_validated_endpoint(monkeypatch) -> None:
    target = parse_disposable_database_target(
        "postgresql://clerk_test:password@127.0.0.1:55432/clerk_test"
    )
    monkeypatch.setattr(offline_network, "_STARTUP_DATABASE_TARGET", target)

    assert offline_network.OFFLINE_NETWORK_GUARD.allowed is False
    assert offline_network.OFFLINE_NETWORK_GUARD.database_target == target

    permitted = offline_network.OFFLINE_NETWORK_GUARD.call(
        lambda address: "connected",
        ("127.0.0.1", 55432),
        operation="socket.socket.connect",
    )

    assert permitted == "connected"
    with pytest.raises(offline_network.OfflineNetworkBlocked):
        offline_network.OFFLINE_NETWORK_GUARD.call(
            lambda address: "unexpected",
            ("127.0.0.1", 443),
            operation="socket.socket.connect",
        )


class _MarkerResult:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> str | None:
        return self.value


class _MarkerConnection:
    def __init__(self, value: str | None, *, fail: bool = False) -> None:
        self.value = value
        self.fail = fail

    def exec_driver_sql(self, statement: str) -> _MarkerResult:
        assert "clerk_test_environment" in statement
        if self.fail:
            raise RuntimeError("driver detail must not escape")
        return _MarkerResult(self.value)


def test_environment_marker_requires_exact_test_value() -> None:
    require_test_environment_marker(_MarkerConnection("test"))

    with pytest.raises(RuntimeError, match="must equal 'test'"):
        require_test_environment_marker(_MarkerConnection("production"))
    with pytest.raises(RuntimeError, match="is missing"):
        require_test_environment_marker(_MarkerConnection(None))
    with pytest.raises(RuntimeError, match="could not be verified") as captured:
        require_test_environment_marker(_MarkerConnection(None, fail=True))

    assert "driver detail" not in str(captured.value)


def test_migration_url_uses_only_validated_test_target_when_opted_in() -> None:
    application_url = "postgresql://production.example.invalid/live"
    test_url = "postgresql://clerk_test:password@127.0.0.1:55432/clerk_test"

    selected = migration_database_url(
        application_url=application_url,
        test_url=test_url,
        database_integration=True,
    )

    assert selected.startswith("postgresql+psycopg://clerk_test:")
    assert "127.0.0.1:55432/clerk_test" in selected
    assert "sslmode=disable" in selected
    assert "production.example.invalid" not in selected

    with pytest.raises(ValueError, match="literal loopback"):
        migration_database_url(
            application_url=application_url,
            test_url="postgresql://user:password@db.example.com:5432/live",
            database_integration=True,
        )


def test_normal_migration_url_keeps_application_target_and_requires_tls() -> None:
    selected = migration_database_url(
        application_url="postgresql://user:password@db.example.com:5432/live",
        test_url=None,
        database_integration=False,
    )

    assert selected.startswith("postgresql+psycopg://")
    assert "db.example.com:5432/live" in selected
    assert "sslmode=require" in selected


def test_target_validator_cli_reports_only_safe_endpoint_metadata() -> None:
    password = "ch08-validator-password-must-not-be-rendered"
    child_env = os.environ.copy()
    child_env["TEST_DATABASE_URL"] = (
        f"postgresql://clerk_test:{password}@127.0.0.1:55432/clerk_test"
    )

    completed = subprocess.run(
        [sys.executable, "-m", "app.database.disposable_target"],
        capture_output=True,
        env=child_env,
        text=True,
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode == 0
    assert rendered.strip() == (
        "database-target-ok host=127.0.0.1 port=55432 database=clerk_test"
    )
    assert password not in rendered


def test_target_validator_cli_rejects_public_target_without_echoing_url() -> None:
    password = "ch08-validator-public-password-must-not-be-rendered"
    child_env = os.environ.copy()
    child_env["TEST_DATABASE_URL"] = (
        "postgresql://clerk_test:"
        f"{password}@aws-0-region.pooler.supabase.com:5432/postgres"
    )

    completed = subprocess.run(
        [sys.executable, "-m", "app.database.disposable_target"],
        capture_output=True,
        env=child_env,
        text=True,
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert rendered.strip() == (
        "database-target-rejected: host must be a literal loopback address"
    )
    assert password not in rendered
