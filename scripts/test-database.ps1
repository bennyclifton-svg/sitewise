[CmdletBinding()]
param(
    [string[]]$NodeId = @("tests/database/test_disposable_migrations.py"),
    [switch]$ValidateOnly,
    [string]$TestDatabaseUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$composeFile = Join-Path $repoRoot "deploy/test/docker-compose.database.yml"

function Assert-CommandSucceeded {
    param([string]$FailureMessage)
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Test-DatabaseTarget {
    param([string]$Url)
    $env:DATABASE_INTEGRATION_TESTS = "1"
    $env:TEST_DATABASE_URL = $Url
    Push-Location $backendDir
    try {
        uv run python -m app.database.disposable_target
        Assert-CommandSucceeded "Disposable database target validation failed."
    }
    finally {
        Pop-Location
    }
}

if ($ValidateOnly) {
    if ([string]::IsNullOrWhiteSpace($TestDatabaseUrl)) {
        throw "-ValidateOnly requires -TestDatabaseUrl."
    }
    Test-DatabaseTarget $TestDatabaseUrl
    exit 0
}

if (-not [string]::IsNullOrWhiteSpace($TestDatabaseUrl)) {
    throw "A normal run creates its own disposable database target."
}

$randomBytes = [byte[]]::new(24)
$randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $randomGenerator.GetBytes($randomBytes)
}
finally {
    $randomGenerator.Dispose()
}
$randomHex = ([BitConverter]::ToString($randomBytes)).Replace("-", "").ToLowerInvariant()
$projectName = "clerk-db-$($randomHex.Substring(0, 12))"
$postgresUser = "clerk_test"
$postgresPassword = $randomHex
$databaseName = "clerk_test_$($randomHex.Substring(0, 12))"
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start()
$databasePort = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
$listener.Stop()
$testDatabaseUrl = (
    "postgresql://$postgresUser`:$postgresPassword@127.0.0.1`:$databasePort/$databaseName"
)

$env:POSTGRES_USER = $postgresUser
$env:POSTGRES_PASSWORD = $postgresPassword
$env:POSTGRES_DB = $databaseName
$env:TEST_DATABASE_PORT = [string]$databasePort
$env:DATABASE_INTEGRATION_TESTS = "1"
$env:TEST_DATABASE_URL = $testDatabaseUrl

$cleanupRequired = $false
$exitCode = 0
$startedAt = [DateTimeOffset]::UtcNow

try {
    Test-DatabaseTarget $testDatabaseUrl

    $cleanupRequired = $true
    docker compose --file $composeFile --project-name $projectName up --detach --wait --wait-timeout 90 database
    Assert-CommandSucceeded "Disposable database did not become healthy."

    $bootstrapSql = @"
CREATE TABLE IF NOT EXISTS clerk_test_environment (
    id smallint PRIMARY KEY CHECK (id = 1),
    environment text NOT NULL
);
INSERT INTO clerk_test_environment (id, environment)
VALUES (1, 'test')
ON CONFLICT (id) DO UPDATE SET environment = EXCLUDED.environment;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
"@
    docker compose --file $composeFile --project-name $projectName exec --no-TTY database psql --username $postgresUser --dbname $databaseName --set ON_ERROR_STOP=1 --command $bootstrapSql
    Assert-CommandSucceeded "Disposable database bootstrap failed."

    Push-Location $backendDir
    try {
        uv run alembic upgrade head
        Assert-CommandSucceeded "Alembic upgrade failed."
        uv run alembic check
        Assert-CommandSucceeded "Alembic schema check failed."
        uv run pytest -m database_integration @NodeId
        Assert-CommandSucceeded "Database integration tests failed."
        uv run alembic heads
        Assert-CommandSucceeded "Alembic head reporting failed."
    }
    finally {
        Pop-Location
    }

    docker compose --file $composeFile --project-name $projectName exec --no-TTY database psql --username $postgresUser --dbname $databaseName --tuples-only --command "SELECT version(); SELECT extname || '=' || extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm') ORDER BY extname;"
    Assert-CommandSucceeded "Database version reporting failed."

    $duration = [DateTimeOffset]::UtcNow - $startedAt
    Write-Host "Database smoke passed in $([int]$duration.TotalSeconds)s."
    Write-Host "Node IDs: $($NodeId -join ', ')"
}
catch {
    Write-Error $_.Exception.Message
    $exitCode = 1
}
finally {
    if ($cleanupRequired) {
        docker compose --file $composeFile --project-name $projectName down --volumes --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Disposable database teardown failed."
            $exitCode = 1
        }
    }
}

exit $exitCode
