# Script untuk preview aplikasi secara lokal sebelum push
# Jalankan dengan: .\preview_local.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ASTROCYCLE LOCAL PREVIEW" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cek apakah Docker sedang berjalan
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker tidak berjalan. Silakan start Docker Desktop terlebih dahulu." -ForegroundColor Red
    exit 1
}
Write-Host "OK - Docker is running" -ForegroundColor Green
Write-Host ""

# Stop container yang sedang berjalan
Write-Host "[2/4] Stopping existing containers..." -ForegroundColor Yellow
docker-compose down > $null 2>&1
Write-Host "OK - Containers stopped" -ForegroundColor Green
Write-Host ""

# Build dan start services
Write-Host "[3/4] Building and starting services..." -ForegroundColor Yellow
Write-Host "    This may take a few minutes..." -ForegroundColor Gray
docker-compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Gagal membangun atau menjalankan services." -ForegroundColor Red
    exit 1
}
Write-Host "OK - Services started" -ForegroundColor Green
Write-Host ""

# Tunggu services siap
Write-Host "[4/4] Waiting for services to be ready..." -ForegroundColor Yellow
Write-Host "    Waiting 15 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 15
Write-Host "OK - Services should be ready" -ForegroundColor Green
Write-Host ""

# Tampilkan informasi akses
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PREVIEW URLS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "Database:  localhost:5432" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Untuk melihat logs:" -ForegroundColor Gray
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "Untuk stop preview:" -ForegroundColor Gray
Write-Host "  docker-compose down" -ForegroundColor White
Write-Host ""

# Buka browser otomatis
Write-Host "Membuka browser..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"
Start-Process "http://localhost:8000/docs"
