$ErrorActionPreference = "Stop"
Write-Host "Initializing CivicLens TN Database..." -ForegroundColor Magenta
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . ".\venv\Scripts\activate.ps1"
}
$env:PYTHONPATH = (Get-Location).Path
python -c "
from backend.database.base_class import Base;
from backend.database.session import engine;
print('Creating tables in database...');
Base.metadata.create_all(bind=engine);
print('Tables created successfully.')
"
Write-Host "Database initialization complete." -ForegroundColor Green
