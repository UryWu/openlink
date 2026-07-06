# start.ps1 — build everything and launch the openlink server.
#
# Mirrors the old start.bat but avoids cmd.exe's CRLF / pushd / multi-line
# if-else quirks. Use:
#   .\start.ps1                                # workspace = openlink repo root
#   .\start.ps1 -Workspace D:\my-project       # AI helpers only see this dir
#   .\start.ps1 -Workspace 'D:\my project'     # spaces are fine
#   .\start.ps1 -Port 40000                    # custom port
#
# Side note: there is no `openlink` console script in pyproject.toml anymore.
# The working command is always `uv run python -m app.main -dir <workspace>`.

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

# ── 2. Dashboard (optional) ──────────────────────────────────────────────

Step 2 'Building dashboard...'
Push-Location (Join-Path $RootDir 'frontend') -StackName openlink-build
try {
    if (Test-Path 'node_modules') {
        Write-Host '  node_modules found, skipping install' -ForegroundColor DarkGray
    } else {
        Write-Host '  installing npm dependencies...'
        & npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed (frontend)' }
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'dashboard build failed, /app/ will not be available'
    } else {
        Write-Host '  dashboard built -> frontend\dist\' -ForegroundColor Green
    }
} finally { Pop-Location -StackName openlink-build }

# ── 3. Backend deps ──────────────────────────────────────────────────────

Step 3 'Installing backend dependencies...'
Push-Location (Join-Path $RootDir 'backend') -StackName openlink-build
try {
    & uv sync
    if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }
    Write-Host '  backend dependencies ready' -ForegroundColor Green
} finally { Pop-Location -StackName openlink-build }

# ── 4. Resolve workspace + start server ──────────────────────────────────

Step 4 "Starting server on port $Port ..."

# Default workspace = openlink repo root
if (-not $Workspace) {
    $Workspace = $RootDir
}

if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
    throw "workspace directory not found: $Workspace"
}

Write-Host ""
Write-Host "  API:           http://127.0.0.1:$Port/health" -ForegroundColor Cyan
Write-Host "  Dashboard:     http://127.0.0.1:$Port/app/"    -ForegroundColor Cyan
Write-Host "  Workspace:     $Workspace"                     -ForegroundColor Cyan
Write-Host "  Load ext:      chrome://extensions/  ->  extension\dist\"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray
Write-Host ""

Push-Location (Join-Path $RootDir 'backend') -StackName openlink-build
try {
    # The `openlink` console script is intentionally absent from pyproject.toml;
    # invoke the module directly so -dir actually reaches the server.
    & uv run python -m app.main -dir $Workspace -port $Port
} finally { Pop-Location -StackName openlink-build }
