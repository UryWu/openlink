param(
    [switch]$Backend
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== openlink build ===" -ForegroundColor Cyan

Write-Host "`n[1/3] build extension..." -ForegroundColor Yellow
Push-Location (Join-Path $root 'extension')
try {
    npx vite build 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "extension build failed" }
} finally { Pop-Location }

Write-Host "`n[2/3] build frontend..." -ForegroundColor Yellow
Push-Location (Join-Path $root 'frontend')
try {
    npx vue-tsc --noEmit 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "frontend typecheck failed" }
    npx vite build 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally { Pop-Location }

if ($Backend) {
    Write-Host "`n[3/3] backend tests..." -ForegroundColor Yellow
    Push-Location (Join-Path $root 'backend')
    try {
        uv run pytest -q 2>&1 | Write-Host
        if ($LASTEXITCODE -ne 0) { throw "backend tests failed" }
    } finally { Pop-Location }
} else {
    Write-Host "`n[3/3] skip backend (use -Backend)" -ForegroundColor DarkGray
}

Write-Host "`n=== done ===" -ForegroundColor Green
