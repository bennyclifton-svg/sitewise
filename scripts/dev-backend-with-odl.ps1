param(
    [int]$ApiPort = 8000,
    [int]$OdlPort = 5002,
    [string]$HostName = "127.0.0.1",
    [ValidateSet("debug", "info", "warning", "error")]
    [string]$OdlLogLevel = "info",
    [switch]$ForceOcr,
    [switch]$NoOcr,
    [string]$OcrEngine = "",
    [string]$OcrLang = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$odlUrl = "http://$HostName`:$OdlPort"

function Test-OdlHealth {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$Url/health" -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    }
    catch {
        return $false
    }
}

function Receive-JobOutput {
    param($Job)

    if ($null -ne $Job) {
        Receive-Job -Job $Job -Keep | Write-Host
    }
}

$startedOdlJob = $null

if (Test-OdlHealth -Url $odlUrl) {
    Write-Host "OpenDataLoader hybrid is already running at $odlUrl"
}
else {
    $odlArgs = @(
        "run",
        "python",
        "-m",
        "opendataloader_pdf.hybrid_server",
        "--host",
        $HostName,
        "--port",
        "$OdlPort",
        "--log-level",
        $OdlLogLevel
    )

    if ($ForceOcr -and $NoOcr) {
        throw "Use either -ForceOcr or -NoOcr, not both."
    }
    if ($ForceOcr) {
        $odlArgs += "--force-ocr"
    }
    if ($NoOcr) {
        $odlArgs += "--no-ocr"
    }
    if ($OcrEngine.Trim()) {
        $odlArgs += @("--ocr-engine", $OcrEngine)
    }
    if ($OcrLang.Trim()) {
        $odlArgs += @("--ocr-lang", $OcrLang)
    }

    Write-Host "Starting OpenDataLoader hybrid at $odlUrl ..."
    $startedOdlJob = Start-Job -Name "clerk-odl-hybrid" -ArgumentList $backendDir, $odlArgs -ScriptBlock {
        param($WorkingDirectory, $Arguments)
        Set-Location $WorkingDirectory
        & uv @Arguments
    }

    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        if ($startedOdlJob.State -ne "Running") {
            Receive-JobOutput -Job $startedOdlJob
            throw "OpenDataLoader hybrid exited before becoming healthy."
        }
        if (Test-OdlHealth -Url $odlUrl) {
            break
        }
        Start-Sleep -Seconds 2
    }

    if (-not (Test-OdlHealth -Url $odlUrl)) {
        Receive-JobOutput -Job $startedOdlJob
        throw "OpenDataLoader hybrid did not become healthy at $odlUrl within 120 seconds."
    }
}

$env:TENDER_ODL_HYBRID_ENABLED = "true"
$env:TENDER_ODL_HYBRID_URL = $odlUrl
$env:TENDER_ODL_HYBRID_MODE = "full"
$env:TENDER_ODL_HYBRID_FALLBACK = "true"

try {
    Write-Host "Starting Clerk backend at http://$HostName`:$ApiPort ..."
    Set-Location $backendDir
    uv run uvicorn app.main:app --reload --host $HostName --port $ApiPort
}
finally {
    if ($null -ne $startedOdlJob) {
        Write-Host "Stopping OpenDataLoader hybrid ..."
        Stop-Job -Job $startedOdlJob -ErrorAction SilentlyContinue
        Remove-Job -Job $startedOdlJob -Force -ErrorAction SilentlyContinue
    }
}
