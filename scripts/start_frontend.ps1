$ErrorActionPreference = "Stop"
Write-Host "Starting CivicLens TN Dashboard..." -ForegroundColor Cyan
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . ".\venv\Scripts\activate.ps1"
} else {
    Write-Warning "Virtual environment not found. Make sure it's created at .\venv"
}
$env:PYTHONPATH = (Get-Location).Path
streamlit run frontend/app.py
