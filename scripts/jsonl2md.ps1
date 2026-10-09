param(
    [string]$InputJsonl = "C:\Users\UryWu\.openlink\conversations.jsonl",
    [string]$OutputMd = ""
)

$pyScript = Join-Path $PSScriptRoot "jsonl2md.py"

if (-not (Test-Path $pyScript)) {
    Write-Error "Python script not found: $pyScript"
    exit 1
}

if (-not (Test-Path $InputJsonl)) {
    Write-Error "Input file not found: $InputJsonl"
    exit 1
}

$argsList = @($pyScript, "-i", $InputJsonl)
if ($OutputMd) {
    $argsList += @("-o", $OutputMd)
}

& python @argsList
