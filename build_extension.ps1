# build_extension.ps1 — build extension only

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Workspace,

    [int]$Port = 39527
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = (Resolve-Path $ScriptDir).Path

function Step($n, $title) {
    Write-Host ""
    Write-Host "[$n/4] $title" -ForegroundColor Cyan
}

# ── 1. Chrome extension ───────────────────────────────────────────────────

Step 1 'Building Chrome extension...'
Push-Location (Join-Path $RootDir 'extension') -StackName openlink-build
try {
    if (Test-Path 'node_modules') {
        Write-Host '  node_modules found, skipping install' -ForegroundColor DarkGray
    } else {
        Write-Host '  installing npm dependencies...'
        & npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed (extension)' }
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'extension build failed (continuing)'
    } else {
        Write-Host '  extension built -> extension\dist\' -ForegroundColor Green
    }
} finally { Pop-Location -StackName openlink-build }

Write-Host "Done. Window closing in 3 seconds..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3