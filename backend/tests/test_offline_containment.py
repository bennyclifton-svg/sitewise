import asyncio
import contextvars
import os
import socket
import subprocess
import sys
import threading
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings, settings
from tests import offline_network as test_bootstrap


def test_imported_settings_and_environment_use_test_sentinels() -> None:
    expected = test_bootstrap.TEST_ENV_SENTINELS

    assert settings.database_url == expected["DATABASE_URL"]
    assert settings.supabase_url == expected["SUPABASE_URL"]
    assert settings.supabase_anon_key == expected["SUPABASE_ANON_KEY"]
    assert settings.supabase_service_role_key == expected["SUPABASE_SERVICE_ROLE_KEY"]
    assert settings.openai_api_key == expected["OPENAI_API_KEY"]
    assert settings.billing_provider == "none"
    assert settings.agent_runtime_enabled is False
    assert settings.agent_web_research_enabled is False
    assert settings.workflow_queue_scope == expected["WORKFLOW_QUEUE_SCOPE"]
    assert settings.build_sha == expected["BUILD_SHA"]

    fresh = Settings()
    assert fresh.database_url == expected["DATABASE_URL"]
    assert fresh.openai_api_key == expected["OPENAI_API_KEY"]

    for key, value in expected.items():
        assert os.environ[key] == value

    scopes = {
        os.environ["AGENT_EXECUTION_SCOPE"],
        os.environ["WORKFLOW_QUEUE_SCOPE"],
        os.environ["TENDER_QUEUE_SCOPE"],
        os.environ["STORAGE_CLEANUP_QUEUE_SCOPE"],
        os.environ["PARSER_QUEUE_SCOPE"],
    }
    assert len(scopes) == 5


def test_unmarked_loopback_connection_is_blocked_before_connecting() -> None:
    blocked = test_bootstrap.OfflineNetworkBlocked

    with pytest.raises(blocked, match="offline pytest blocked"):
        httpx.get("http://127.0.0.1:9", timeout=0.01)
    with pytest.raises(blocked, match="socket.getaddrinfo"):
        socket.getaddrinfo("example.invalid", 443)
    with pytest.raises(blocked, match="socket.create_connection"):
        socket.create_connection(("127.0.0.1", 9), timeout=0.01)
    with socket.socket() as stream:
        with pytest.raises(blocked, match="socket.socket.connect"):
            stream.connect(("127.0.0.1", 9))
    with socket.socket() as stream:
        with pytest.raises(blocked, match="socket.socket.connect_ex"):
            stream.connect_ex(("127.0.0.1", 9))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
        with pytest.raises(blocked, match="socket.socket.sendto"):
            datagram.sendto(b"blocked", ("127.0.0.1", 9))


def test_network_policy_requires_approved_marker_and_explicit_opt_in() -> None:
    permits = test_bootstrap.network_access_permitted

    assert permits(set(), "1") is False
    assert permits({"integration"}, None) is False
    assert permits({"integration"}, "0") is False
    assert permits({"tender_eval"}, "true") is False
    assert permits({"integration"}, "1") is True
    assert permits({"tender_eval"}, "1") is True
    assert permits({"integration"}, " 1") is False
    assert permits({"integration"}, "01") is False
    assert permits({"integration"}, "true") is False


def test_runtime_env_mutation_cannot_enable_network(monkeypatch) -> None:
    assert test_bootstrap.startup_network_access_permitted({"integration"}) is False

    monkeypatch.setenv("CLERK_TEST_ALLOW_NETWORK", "1")

    assert test_bootstrap.startup_network_access_permitted({"integration"}) is False


def test_guard_delegates_only_when_policy_has_already_permitted_network() -> None:
    fake_original = Mock(return_value="fake socket result")

    with pytest.raises(test_bootstrap.OfflineNetworkBlocked):
        test_bootstrap.OFFLINE_NETWORK_GUARD.call(
            fake_original,
            ("example.invalid", 443),
            allowed_for_test=False,
        )

    result = test_bootstrap.OFFLINE_NETWORK_GUARD.call(
        fake_original,
        ("example.invalid", 443),
        allowed_for_test=True,
    )

    assert result == "fake socket result"
    fake_original.assert_called_once_with(("example.invalid", 443))


def test_guard_installation_is_idempotent() -> None:
    guarded_create_connection = socket.create_connection

    test_bootstrap.OFFLINE_NETWORK_GUARD.install()

    assert socket.create_connection is guarded_create_connection


def test_authority_does_not_bleed_into_a_later_test_generation() -> None:
    guard = type(test_bootstrap.OFFLINE_NETWORK_GUARD)()
    first = guard.begin_test(allowed=True)
    stale_context = contextvars.copy_context()
    guard.end_test(first)
    second = guard.begin_test(allowed=True)

    try:
        assert guard.call(Mock(return_value="current")) == "current"
        with pytest.raises(test_bootstrap.OfflineNetworkBlocked):
            stale_context.run(guard.call, Mock(return_value="stale"))
    finally:
        guard.end_test(second)


def test_raw_background_thread_does_not_inherit_network_authority() -> None:
    guard = type(test_bootstrap.OFFLINE_NETWORK_GUARD)()
    lease = guard.begin_test(allowed=True)
    results: list[BaseException | str] = []

    def exercise() -> None:
        try:
            results.append(guard.call(Mock(return_value="unexpected")))
        except BaseException as exc:  # captured for assertion on the main thread
            results.append(exc)

    worker = threading.Thread(target=exercise)
    try:
        worker.start()
        worker.join(timeout=2)
    finally:
        guard.end_test(lease)

    assert worker.is_alive() is False
    assert len(results) == 1
    assert isinstance(results[0], test_bootstrap.OfflineNetworkBlocked)


def test_stale_async_task_is_denied_during_a_later_generation() -> None:
    guard = type(test_bootstrap.OFFLINE_NETWORK_GUARD)()

    async def exercise() -> None:
        resume = asyncio.Event()
        ready = asyncio.Event()
        first = guard.begin_test(allowed=True)

        async def stale_work() -> None:
            ready.set()
            await resume.wait()
            with pytest.raises(test_bootstrap.OfflineNetworkBlocked):
                guard.call(Mock(return_value="stale"))

        stale_task = asyncio.create_task(stale_work())
        await ready.wait()
        guard.end_test(first)
        second = guard.begin_test(allowed=True)
        try:
            resume.set()
            await stale_task
        finally:
            guard.end_test(second)

    asyncio.run(exercise())


def test_child_python_process_inherits_test_sentinels() -> None:
    expected = dict(test_bootstrap.TEST_ENV_SENTINELS)
    script = (
        "import os; "
        f"expected = {expected!r}; "
        "mismatched = [key for key, value in expected.items() "
        "if os.environ.get(key) != value]; "
        "assert not mismatched, mismatched; "
        "print('sentinels-ok')"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "sentinels-ok"


def test_generic_network_opt_in_cannot_restore_a_database_target() -> None:
    sentinel_database_url = test_bootstrap.TEST_ENV_SENTINELS["TEST_DATABASE_URL"]
    child_env = os.environ.copy()
    child_env.update(
        {
            "CLERK_TEST_ALLOW_NETWORK": "1",
            "TEST_DATABASE_URL": "postgresql://production.example.invalid/live",
            "ALLOW_DESTRUCTIVE_TEST_DATABASE": "1",
        }
    )
    script = (
        "import os; import tests.offline_network; "
        f"assert os.environ['TEST_DATABASE_URL'] == {sentinel_database_url!r}; "
        "assert os.environ['ALLOW_DESTRUCTIVE_TEST_DATABASE'] == '0'; "
        "print('database-contained')"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        env=child_env,
        text=True,
    )

    assert completed.stdout.strip() == "database-contained"


def test_asyncio_and_in_process_asgi_do_not_need_network() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    async def exercise() -> None:
        await asyncio.sleep(0)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get("/health")
        assert response.json() == {"status": "ok"}

    asyncio.run(exercise())


@pytest.mark.integration
def test_marked_test_with_startup_opt_in_can_delegate_to_a_fake() -> None:
    assert test_bootstrap.OFFLINE_NETWORK_GUARD.allowed is True
    assert os.environ["TEST_DATABASE_URL"] == test_bootstrap.TEST_ENV_SENTINELS[
        "TEST_DATABASE_URL"
    ]
    assert os.environ["ALLOW_DESTRUCTIVE_TEST_DATABASE"] == "0"
    fake_original = Mock(return_value="allowed-without-network")

    result = test_bootstrap.OFFLINE_NETWORK_GUARD.call(fake_original)

    assert result == "allowed-without-network"
    fake_original.assert_called_once_with()
