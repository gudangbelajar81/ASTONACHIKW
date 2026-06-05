# PowerShell script: setup root venv, install backend deps, migrate, and run backend.
$ErrorActionPreference = 'Stop'

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $backendDir
Set-Location $root

$pythonVersionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonVersion = [version]$pythonVersionOutput
if ($pythonVersion.Major -ne 3 -or $pythonVersion.Minor -gt 12) {
    throw "AstroCycle backend dependencies are pinned for Python 3.12 or lower. Found Python $pythonVersionOutput. Install Python 3.11 or 3.12 and recreate .venv."
}

if (-not (Test-Path .venv)) {
    python -m venv .venv
}

$activate = Join-Path $root '.venv\Scripts\Activate.ps1'
Write-Host "Activating venv..."
. $activate

Write-Host "Installing backend dependencies..."
pip install -r backend\requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Copied .env.example to .env - please edit .env and set OPENAI_API_KEY and DATABASE_URL as needed."
}

Write-Host "Running DB migrations (alembic)..."
Set-Location $root
alembic -c backend\alembic.ini upgrade head
Set-Location $root

Write-Host "Starting backend (uvicorn)..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
