# Orchestrator: bring up Docker DB, run migrations, seed, start backend and frontend.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pythonVersionOutput = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonVersion = [version]$pythonVersionOutput
if ($pythonVersion.Major -ne 3 -or $pythonVersion.Minor -gt 12) {
    throw "AstroCycle backend dependencies are pinned for Python 3.12 or lower. Found Python $pythonVersionOutput. Install Python 3.11 or 3.12 and recreate .venv."
}

Write-Host "1) Starting PostgreSQL via docker-compose..."
docker-compose up -d

Write-Host "Waiting for PostgreSQL to accept connections on port 5432..."
$maxWait = 60
$waited = 0
while ($waited -lt $maxWait) {
    $conn = Test-NetConnection -ComputerName '127.0.0.1' -Port 5432 -WarningAction SilentlyContinue
    if ($conn.TcpTestSucceeded) { break }
    Start-Sleep -Seconds 2
    $waited += 2
}
if ($waited -ge $maxWait) {
    Write-Host "Warning: Postgres did not become ready within $maxWait seconds."
}

Write-Host "2) Prepare Python virtualenv and install backend deps..."
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Copied .env.example to .env - please edit .env if needed (OPENAI_API_KEY, DATABASE_URL)"
}

if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $parts = $line -split '=', 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim().Trim('"')
                Set-Item -Path "Env:$key" -Value $value
            }
        }
    }
}

Write-Host "3) Run DB migrations..."
Set-Location $root
alembic -c backend\alembic.ini upgrade head
Set-Location $root

Write-Host "4) Seed data (AAPL, 365 days)..."
Set-Location $root
.\backend\run_seed.ps1 -Symbol AAPL -Days 365
Set-Location $root

Write-Host "5) Start backend (uvicorn) as background process..."
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $pythonPath = $venvPython
} else {
    $pythonPath = "python"
}

$uvicornArgs = "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
$backendProc = Start-Process -FilePath $pythonPath -ArgumentList $uvicornArgs -WorkingDirectory $root -PassThru
Write-Host "Backend started with PID $($backendProc.Id)"

Write-Host "6) Prepare frontend dependencies..."
$frontendDir = Join-Path $root 'frontend'
npm install --prefix $frontendDir --no-audit --no-fund --strict-ssl=false --cache (Join-Path $frontendDir '.npm-cache')

Write-Host "7) Start frontend (npm run dev) as background process..."
$frontendProc = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -PassThru
Write-Host "Frontend started with PID $($frontendProc.Id)"

Write-Host "All services started. Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:3000"
Write-Host "To stop processes: Stop-Process -Id <PID> (use the PIDs shown above)."
