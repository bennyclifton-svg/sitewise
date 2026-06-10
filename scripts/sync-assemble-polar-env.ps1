param(
    [string]$AssembleEnvPath = "D:\AI Projects\assemble.ai P2\assemble.ai\.env.local",
    [string]$TargetEnvPath = "D:\AI Projects\clerk\backend\.env"
)

$keys = @(
    "POLAR_ACCESS_TOKEN",
    "POLAR_WEBHOOK_SECRET",
    "POLAR_STARTER_PRODUCT_ID",
    "POLAR_PROFESSIONAL_PRODUCT_ID"
)

if (-not (Test-Path -LiteralPath $AssembleEnvPath)) {
    throw "Assemble env file not found: $AssembleEnvPath"
}

$source = @{}
foreach ($line in Get-Content -LiteralPath $AssembleEnvPath) {
    if ($line -match '^\s*#' -or $line -notmatch '=') {
        continue
    }

    $name, $value = $line -split '=', 2
    $name = $name.Trim()
    if ($keys -contains $name -and -not [string]::IsNullOrWhiteSpace($value)) {
        $source[$name] = $value.Trim()
    }
}

$missing = $keys | Where-Object { -not $source.ContainsKey($_) }
if ($missing.Count -gt 0) {
    throw "Missing Polar keys in Assemble env: $($missing -join ', ')"
}

$targetLines = @()
if (Test-Path -LiteralPath $TargetEnvPath) {
    $targetLines = @(Get-Content -LiteralPath $TargetEnvPath)
} else {
    $example = Join-Path (Split-Path -Parent $TargetEnvPath) ".env.example"
    if (Test-Path -LiteralPath $example) {
        $targetLines = @(Get-Content -LiteralPath $example)
    }
}

$seen = @{}
$updated = foreach ($line in $targetLines) {
    if ($line -match '^([A-Z0-9_]+)=') {
        $name = $Matches[1]
        if ($source.ContainsKey($name)) {
            $seen[$name] = $true
            "$name=$($source[$name])"
            continue
        }
    }
    $line
}

foreach ($key in $keys) {
    if (-not $seen.ContainsKey($key)) {
        $updated += "$key=$($source[$key])"
    }
}

$targetDir = Split-Path -Parent $TargetEnvPath
if (-not (Test-Path -LiteralPath $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

Set-Content -LiteralPath $TargetEnvPath -Value $updated -Encoding utf8
Write-Output "Synced Polar env keys into $TargetEnvPath"
