$ErrorActionPreference = "Stop"
Write-Host "Running CivicLens TN Test Suite..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . ".\venv\Scripts\activate.ps1"
}
$env:PYTHONPATH = (Get-Location).Path
pytest tests/
