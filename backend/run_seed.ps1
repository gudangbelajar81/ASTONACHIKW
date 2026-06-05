param(
    [string]$Symbol = "AAPL",
    [int]$Days = 365
)

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

. .\.venv\Scripts\Activate.ps1

Write-Host "Installing backend dependencies (if needed)..."
pip install -r backend\requirements.txt

Write-Host "Seeding data for $Symbol, last $Days days..."
python -m backend.seeds.seed_data --symbol $Symbol --days $Days
