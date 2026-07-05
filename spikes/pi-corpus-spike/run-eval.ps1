param(
    [ValidateSet("locked", "open")]
    [string]$Condition = "locked",
    [int]$TimeoutSeconds = 180
)

if (-not $env:CLERK_MCP_TOKEN) { throw "CLERK_MCP_TOKEN not set - mint a token first (Task 3)" }
if (-not $env:SPIKE_PROJECT_ID) { throw "SPIKE_PROJECT_ID not set" }
if (-not $env:OPENAI_API_KEY) {
    $envFile = Join-Path $PSScriptRoot "..\..\backend\.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^OPENAI_API_KEY=(.+)$') { $env:OPENAI_API_KEY = $matches[1] }
        }
    }
    if (-not $env:OPENAI_API_KEY) { throw "OPENAI_API_KEY not set" }
}

$spikeDir = $PSScriptRoot
$env:PI_OFFLINE = "1"
Set-Location $spikeDir

New-Item -ItemType Directory -Force "results" | Out-Null
$questions = Get-Content "questions.txt" | Where-Object { $_.Trim() }

$preamble = "You are answering questions about project $($env:SPIKE_PROJECT_ID). " +
    "Its uploaded documents are already ingested and fully searchable via the clerk tools. " +
    "Question: "

function Invoke-PiPrompt {
    param(
        [string]$Prompt,
        [bool]$Locked,
        [string]$SpikeDir,
        [string]$OpenAiKey,
        [string]$McpToken,
        [int]$Timeout
    )

    $job = Start-Job -ArgumentList @($Prompt, $Locked, $SpikeDir, $OpenAiKey, $McpToken) -ScriptBlock {
        param($Prompt, $Locked, $SpikeDir, $OpenAiKey, $McpToken)
        $env:OPENAI_API_KEY = $OpenAiKey
        $env:CLERK_MCP_TOKEN = $McpToken
        $env:PI_OFFLINE = "1"
        Set-Location $SpikeDir
        if ($Locked) {
            & pi --no-tools --provider openai --model gpt-5.1 --thinking off --no-session --mode json -p $Prompt 2>&1 | Out-String
        } else {
            & pi --provider openai --model gpt-5.1 --thinking off --no-session --mode json -p $Prompt 2>&1 | Out-String
        }
    }

    $null = Wait-Job $job -Timeout $Timeout
    if ($job.State -eq "Running") {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
        return '{"error":"timeout","timeout_seconds":' + $Timeout + '}'
    }

    $output = Receive-Job $job
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    return $output
}

$i = 0
foreach ($q in $questions) {
    $i++
    $outFile = "results/$Condition-q$i.json"
    Write-Host "[$Condition] Q$i : $q"
    $prompt = $preamble + $q
    $locked = ($Condition -eq "locked")
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-PiPrompt -Prompt $prompt -Locked $locked -SpikeDir $spikeDir `
        -OpenAiKey $env:OPENAI_API_KEY -McpToken $env:CLERK_MCP_TOKEN -Timeout $TimeoutSeconds
    $sw.Stop()
    $result | Set-Content -Path $outFile -Encoding utf8
    Write-Host "  -> $outFile ($([math]::Round($sw.Elapsed.TotalSeconds, 1))s)"
}

Write-Host "Done. Traces in results/ - score them into results.md"
