# Docker Desktop Fix Guide

## Problem
Docker Desktop is returning `500 Internal Server Error` when trying to access the API.

## Solutions

### Option 1: Restart Docker Desktop (Recommended)
1. Open Docker Desktop application
2. Click on the Docker icon in system tray
3. Select "Quit Docker Desktop"
4. Wait 10 seconds
5. Start Docker Desktop again
6. Wait for Docker to fully start (whale icon should be steady, not animated)
7. Test with: `docker ps`

### Option 2: Restart Docker Service (Windows)
```powershell
# Run as Administrator
Restart-Service docker
```

### Option 3: Full Docker Reset
1. Open Docker Desktop
2. Go to Settings (gear icon)
3. Select "Troubleshoot"
4. Click "Reset to factory defaults"
5. Restart Docker Desktop

### Option 4: Use Local PostgreSQL Instead
If Docker continues to have issues, you can install PostgreSQL locally:

1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Install with default settings
3. During installation, set password to: `password`
4. Keep default port: `5432`
5. Database will be accessible at: `localhost:5432`

The `.env` file is already configured for this setup:
```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/astrocycle
```

### After Docker is Fixed

Run this command to start PostgreSQL:
```powershell
docker-compose up -d
```

Verify it's running:
```powershell
docker ps
```

You should see a container named `astonachikw-postgres-1` or similar.

### Test Database Connection

Once PostgreSQL is running, test the connection:
```powershell
# Using psql (if installed)
psql -h localhost -U postgres -d astrocycle

# Or using Docker
docker exec -it astonachikw-postgres-1 psql -U postgres -d astrocycle
```

Password: `password`
