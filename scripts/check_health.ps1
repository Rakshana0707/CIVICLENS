$ErrorActionPreference = "Stop"
Write-Host "Checking CivicLens TN Health..." -ForegroundColor Cyan
if (Test-Path ".\venv\Scripts\activate.ps1") {
    . ".\venv\Scripts\activate.ps1"
}
python -c "
import requests, sys
print('--- CivicLens TN Health Check ---')
try:
    api_res = requests.get('http://localhost:5000/health', timeout=5).json()
    print(f'✅ Backend API: {api_res.get(`'message`', `'Unknown`')}')
except Exception as e:
    print('❌ Backend API: Down or Unreachable')
    
try:
    db_res = requests.get('http://localhost:5000/health/db', timeout=5).json()
    if db_res.get('status') == 'success':
        print(f'✅ Database: {db_res.get(`'message`', `'Connected`')}')
    else:
        print(f'❌ Database: Error - {db_res.get(`'details`', `'Unknown error`')}')
except Exception as e:
    print('❌ Database Health Check Failed')
"
