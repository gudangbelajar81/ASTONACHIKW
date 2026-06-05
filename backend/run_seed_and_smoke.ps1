$ErrorActionPreference = 'Stop'

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $backendDir
Set-Location $root

$pythonVersionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonVersion = [version]$pythonVersionOutput
if ($pythonVersion.Major -ne 3 -or $pythonVersion.Minor -gt 12) {
    throw "AstroCycle backend dependencies are pinned for Python 3.12 or lower. Found Python $pythonVersionOutput. Install Python 3.12 and recreate .venv."
}

if (-not (Test-Path .venv)) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

pip install -r backend\requirements.txt

Write-Host "Running seed script..."
.\backend\run_seed.ps1 -Symbol AAPL -Days 365

Write-Host "Starting backend (uvicorn) in background..."
$proc = Start-Process -FilePath "python" -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $root -PassThru

$maxWait = 60
$elapsed = 0
$up = $false
while ($elapsed -lt $maxWait) {
    try {
        $resp = Invoke-RestMethod -Uri http://127.0.0.1:8000/health -TimeoutSec 2
        if ($resp.status -eq 'ok') { $up = $true; break }
    } catch {
        Start-Sleep -Seconds 1
        $elapsed += 1
    }
}

if (-not $up) {
    Write-Host "Backend did not become ready within $maxWait seconds. Killing process and exiting."
    Stop-Process -Id $proc.Id -Force
    exit 1
}

Write-Host "Backend is up. Running smoke checks..."

try {
    $h = Invoke-RestMethod -Uri http://127.0.0.1:8000/health -TimeoutSec 5
    Write-Host "Health:" $h
} catch { Write-Host "Health check failed: $_" }

try {
    $p = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/planets -TimeoutSec 10
    Write-Host "Planets date:" $p.date
} catch { Write-Host "Planets check failed: $_" }

$end = Get-Date
$start = $end.AddDays(-7)
$startStr = $start.ToString('yyyy-MM-dd')
$endStr = $end.ToString('yyyy-MM-dd')
$cycleUrl = "http://127.0.0.1:8000/api/cycle?planet_a=Sun&planet_b=Moon&start_date=$startStr&end_date=$endStr"
try {
    $c = Invoke-RestMethod -Uri $cycleUrl -TimeoutSec 15
    Write-Host "Cycle points returned:" ($c.Count)
} catch { Write-Host "Cycle check failed: $_" }

Write-Host "Smoke tests completed. Stopping backend process..."
Stop-Process -Id $proc.Id -Force

Write-Host "Done."
