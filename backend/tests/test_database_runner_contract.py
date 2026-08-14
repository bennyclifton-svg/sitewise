from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "deploy" / "test" / "docker-compose.database.yml"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "test-database.ps1"
CI_FILE = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_database_compose_is_private_ephemeral_and_digest_pinned() -> None:
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    database = compose["services"]["database"]

    assert re.fullmatch(
        r"pgvector/pgvector:pg16@sha256:[0-9a-f]{64}",
        database["image"],
    )
    assert database["ports"] == ["127.0.0.1:${TEST_DATABASE_PORT}:5432"]
    assert database["tmpfs"] == [
        "/var/lib/postgresql/data:rw,noexec,nosuid,size=1g"
    ]
    assert database["healthcheck"]["test"][0:2] == ["CMD-SHELL", "pg_isready"]
    assert compose["networks"]["database_test"]["internal"] is True
    assert "volumes" not in compose


def test_database_runner_has_fail_closed_lifecycle_and_shared_commands() -> None:
    source = RUNNER_SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$ValidateOnly" in source
    assert '$env:DATABASE_INTEGRATION_TESTS = "1"' in source
    assert '$env:TEST_DATABASE_URL = $testDatabaseUrl' in source
    assert "docker compose" in source
    assert "up --detach --wait" in source
    assert "CREATE TABLE IF NOT EXISTS clerk_test_environment" in source
    assert "uv run alembic upgrade head" in source
    assert "uv run alembic check" in source
    assert 'uv run pytest -m database_integration' in source
    assert "finally" in source
    assert "down --volumes --remove-orphans" in source


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required to verify the repository runner")
    return executable


def _validate_with_runner(url: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER_SCRIPT),
            "-ValidateOnly",
            "-TestDatabaseUrl",
            url,
        ],
        capture_output=True,
        text=True,
    )


def test_database_runner_validation_never_starts_docker_or_echoes_password() -> None:
    password = "ch08-runner-password-must-not-be-rendered"

    completed = _validate_with_runner(
        f"postgresql://clerk_test:{password}@127.0.0.1:55432/clerk_test"
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode == 0, rendered
    assert "database-target-ok host=127.0.0.1 port=55432 database=clerk_test" in rendered
    assert password not in rendered
    assert "docker" not in rendered.lower()


def test_database_runner_rejects_provider_target_before_docker() -> None:
    password = "ch08-runner-public-password-must-not-be-rendered"

    completed = _validate_with_runner(
        "postgresql://clerk_test:"
        f"{password}@aws-0-region.pooler.supabase.com:5432/postgres"
    )

    rendered = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "literal loopback address" in rendered
    assert password not in rendered
    assert "docker" not in rendered.lower()


def test_database_runner_arms_teardown_before_compose_start() -> None:
    source = RUNNER_SCRIPT.read_text(encoding="utf-8")

    cleanup_assignment = source.index("$cleanupRequired = $true")
    compose_start = source.index("up --detach --wait")
    finally_block = source.index("finally", compose_start)
    cleanup_guard = source.index("if ($cleanupRequired)", finally_block)
    compose_down = source.index("down --volumes --remove-orphans", cleanup_guard)

    assert cleanup_assignment < compose_start < finally_block
    assert finally_block < cleanup_guard < compose_down


def _write_failing_docker(fake_bin: Path) -> None:
    if os.name == "nt":
        executable = fake_bin / "docker.cmd"
        executable.write_text(
            "@echo off\n"
            '>> "%FAKE_DOCKER_LOG%" echo %*\n'
            'echo %* | findstr /C:" up " >nul\n'
            "if %errorlevel% equ 0 exit /b 42\n"
            "exit /b 0\n",
            encoding="utf-8",
        )
        return
    executable = fake_bin / "docker"
    executable.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$FAKE_DOCKER_LOG\"\n"
        'case " $* " in *" up "*) exit 42 ;; esac\n'
        "exit 0\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)


def test_database_runner_tears_down_after_partial_compose_failure(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_failing_docker(fake_bin)
    child_env = os.environ.copy()
    child_env["PATH"] = f"{fake_bin}{os.pathsep}{child_env['PATH']}"
    child_env["FAKE_DOCKER_LOG"] = str(docker_log)

    completed = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER_SCRIPT),
        ],
        capture_output=True,
        env=child_env,
        text=True,
    )

    rendered = completed.stdout + completed.stderr
    assert docker_log.exists(), rendered
    calls = docker_log.read_text(encoding="utf-8").splitlines()
    assert completed.returncode != 0
    assert "up --detach --wait" in calls[0]
    assert "down --volumes --remove-orphans" in calls[-1]
    assert re.search(r"--project-name (\S+)", calls[0]).group(1) == re.search(
        r"--project-name (\S+)", calls[-1]
    ).group(1)
    assert "postgresql://" not in rendered


def test_database_smoke_ci_is_manual_private_and_uses_shared_runner() -> None:
    workflow = yaml.safe_load(CI_FILE.read_text(encoding="utf-8"))
    database_job = workflow["jobs"]["database-smoke"]
    triggers = workflow.get("on", workflow.get(True, {}))

    assert "workflow_dispatch" in triggers
    assert database_job["if"] == "github.event_name == 'workflow_dispatch'"
    assert database_job["timeout-minutes"] <= 15
    runner_steps = [
        step
        for step in database_job["steps"]
        if step.get("name") == "Run disposable database smoke"
    ]
    assert runner_steps == [
        {
            "name": "Run disposable database smoke",
            "shell": "pwsh",
            "run": "./scripts/test-database.ps1",
        }
    ]
