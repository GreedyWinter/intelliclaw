$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $python)) {
    throw "Backend virtualenv Python not found at $python"
}

Set-Location $repoRoot
& $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
