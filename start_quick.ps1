# start_quick.ps1 — launch only the openlink backend, skip all builds.
#
# Use when the extension and dashboard are already built and you just want
# the FastAPI server up fast:
#   .\start_quick.ps1                                # workspace = openlink repo root
#   .\start_quick.ps1 D:\my-project                  # positional workspace arg (shorthand)
#   .\start_quick.ps1 -Workspace D:\my-project       # AI helpers only see this dir
#   .\start_quick.ps1 -Workspace 'D:\my project'     # spaces are fine
#   .\start_quick.ps1 -Port 40000                    # custom port
#
# IMPORTANT: pass the workspace path from PowerShell. When this script is
# invoked from cmd.exe, the path argument is dropped, so the root directory
# falls back to the current path.
#
# Note: this does NOT run `uv sync`. Run it once manually if the venv
# hasn't been created yet — `uv run` will auto-sync on first invocation.

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Workspace,

    [int]$Port = 39527
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = (Resolve-Path $ScriptDir).Path

# Default workspace = openlink repo root
if (-not $Workspace) {
    $Workspace = $RootDir
}

if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
    throw "workspace directory not found: $Workspace"
}

Write-Host ""
Write-Host "  API:        http://127.0.0.1:$Port/health" -ForegroundColor Cyan
Write-Host "  Workspace:  $Workspace"                     -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray
Write-Host ""

Push-Location (Join-Path $RootDir 'backend') -StackName openlink-build
try {
    & uv run python -m app.main -dir $Workspace -port $Port
} finally { Pop-Location -StackName openlink-build }
