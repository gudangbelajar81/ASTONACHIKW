# Health Check Script for ASTONACHIKW
# Run this script to verify application status before pushing

Write-Host "=== ASTONACHIKW Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check Backend Status
Write-Host "1. Checking Backend Status..." -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "https://astonachikw-production.up.railway.app/health" -Method GET -TimeoutSec 10
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "   ✅ Backend is ONLINE at https://astonachikw-production.up.railway.app" -ForegroundColor Green
        Write-Host "   Response: $($backendResponse.Content)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠ Backend returned status: $($backendResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Backend is OFFLINE or unreachable" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check Backend Docs
Write-Host "2. Checking Backend Documentation..." -ForegroundColor Yellow
try {
    $docsResponse = Invoke-WebRequest -Uri "https://astonachikw-production.up.railway.app/docs" -Method GET -TimeoutSec 10
    if ($docsResponse.StatusCode -eq 200) {
        Write-Host "   ✅ Backend docs available at https://astonachikw-production.up.railway.app/docs" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Docs returned status: $($docsResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Backend docs unavailable" -ForegroundColor Red
}

Write-Host ""

# Check Local Frontend (if running)
Write-Host "3. Checking Local Frontend..." -ForegroundColor Yellow
$localPorts = @(3000, 3001, 3002, 3003)
$frontendRunning = $false

foreach ($port in $localPorts) {
    try {
        $localResponse = Invoke-WebRequest -Uri "http://localhost:$port" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($localResponse.StatusCode -eq 200) {
            Write-Host "   ✅ Frontend running at http://localhost:$port" -ForegroundColor Green
            $frontendRunning = $true
            break
        }
    } catch {
        # Port not responding, continue checking
    }
}

if (-not $frontendRunning) {
    Write-Host "   ℹ Frontend not detected on common ports (3000-3003)" -ForegroundColor Gray
    Write-Host "   To start frontend: cd frontend; npm run dev" -ForegroundColor Gray
}

Write-Host ""

# Check Frontend Build Status
Write-Host "4. Checking Frontend Build Status..." -ForegroundColor Yellow
if (Test-Path "frontend/.next") {
    Write-Host "   ✅ Frontend build directory exists (.next/)" -ForegroundColor Green
} else {
    Write-Host "   ℹ Frontend not built yet" -ForegroundColor Gray
    Write-Host "   To build: cd frontend; npm run build" -ForegroundColor Gray
}

Write-Host ""

# Check Environment Variables
Write-Host "5. Checking Environment Configuration..." -ForegroundColor Yellow
if (Test-Path "frontend/.env.local") {
    Write-Host "   ✅ Local environment file exists (frontend/.env.local)" -ForegroundColor Green
    $envContent = Get-Content "frontend/.env.local" -Raw
    if ($envContent -match "NEXT_PUBLIC_BACKEND_URL") {
        Write-Host "   ✅ NEXT_PUBLIC_BACKEND_URL is configured" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ NEXT_PUBLIC_BACKEND_URL not found in .env.local" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠ Local environment file missing" -ForegroundColor Yellow
    Write-Host "   Create: frontend/.env.local with NEXT_PUBLIC_BACKEND_URL" -ForegroundColor Gray
}

Write-Host ""

# Git Status Check
Write-Host "6. Checking Git Status..." -ForegroundColor Yellow
try {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Host "   ⚠ Uncommitted changes detected:" -ForegroundColor Yellow
        $gitStatus | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
        Write-Host "   Run: git add . && git commit -m 'your message'" -ForegroundColor Gray
    } else {
        Write-Host "   ✅ No uncommitted changes" -ForegroundColor Green
    }
} catch {
    Write-Host "   ℹ Git not available or not a git repository" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Quick Links ===" -ForegroundColor Cyan
Write-Host "Backend Health:    https://astonachikw-production.up.railway.app/health" -ForegroundColor White
Write-Host "Backend Docs:      https://astonachikw-production.up.railway.app/docs" -ForegroundColor White
Write-Host "Backend API Root:  https://astonachikw-production.up.railway.app" -ForegroundColor White
Write-Host "Local Frontend:    http://localhost:3000 (or 3001, 3002, 3003)" -ForegroundColor White
Write-Host ""
Write-Host "=== Commands ===" -ForegroundColor Cyan
Write-Host "Start frontend:    cd frontend; npm run dev" -ForegroundColor White
Write-Host "Build frontend:    cd frontend; npm run build" -ForegroundColor White
Write-Host "Check backend:     curl https://astonachikw-production.up.railway.app/health" -ForegroundColor White
Write-Host ""
Write-Host "=== Status Summary ===" -ForegroundColor Cyan
Write-Host "✅ Ready to push if:" -ForegroundColor Green
Write-Host "   1. Backend is online" -ForegroundColor Gray
Write-Host "   2. Frontend builds successfully" -ForegroundColor Gray
Write-Host "   3. No critical errors in health check" -ForegroundColor Gray
Write-Host ""