# Railway Deployment Guide for ASTONACHIKW Frontend

## Status
✅ **Frontend ready for Railway deployment**
✅ **Backend already deployed:** https://astonachikw-production.up.railway.app
✅ **API URL refactoring completed:** All frontend pages use `getApiBaseUrl()` helper

## Environment Variables for Railway

### Required Environment Variables:
```bash
NEXT_PUBLIC_BACKEND_URL=https://astonachikw-production.up.railway.app
```

### Optional (fallback):
```bash
NEXT_PUBLIC_API_URL=https://astonachikw-production.up.railway.app
```

## How to Deploy Frontend to Railway

### Option 1: Deploy via Railway Dashboard
1. Go to [Railway.app](https://railway.app)
2. Create new project → "Deploy from GitHub repo"
3. Select your ASTONACHIKW repository
4. Set environment variables:
   - `NEXT_PUBLIC_BACKEND_URL`: `https://astonachikw-production.up.railway.app`
5. Railway will automatically detect and deploy the frontend

### Option 2: Deploy via Railway CLI
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to existing project
railway link

# Set environment variable
railway variables set NEXT_PUBLIC_BACKEND_URL https://astonachikw-production.up.railway.app

# Deploy
railway up
```

## Configuration Files

### 1. `frontend/railway.toml`
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "npm run start"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 2. `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
```

### 3. `frontend/.env.railway` (reference)
```bash
# Railway deployment configuration
NEXT_PUBLIC_BACKEND_URL=https://astonachikw-production.up.railway.app
NEXT_PUBLIC_API_URL=https://astonachikw-production.up.railway.app
```

## API URL Helper Function

All frontend API calls use the centralized helper:

```typescript
// frontend/lib/apiBase.ts
export function getApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (configuredUrl) return configuredUrl;
  if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
    return "https://astonachikw-production.up.railway.app";
  }
  return "http://127.0.0.1:8000";
}
```

### Priority Order:
1. `NEXT_PUBLIC_BACKEND_URL` (highest priority)
2. `NEXT_PUBLIC_API_URL` (fallback)
3. Railway auto-detection (if hostname ends with `.up.railway.app`)
4. Local development (`http://127.0.0.1:8000`)

## Files Modified for Railway Compatibility

### Frontend Pages Updated (6 files):
1. `frontend/app/workflow/page.tsx`
2. `frontend/app/watchlist/page.tsx`
3. `frontend/app/backtest/page.tsx`
4. `frontend/app/alerts/page.tsx`
5. `frontend/app/dashboard/page.tsx`
6. `frontend/app/login/page.tsx`

### Changes Made:
- ✅ Removed hard-coded API URLs
- ✅ Added `import { getApiBaseUrl } from "../../lib/apiBase"`
- ✅ Replaced `API_BASE_URL` with `getApiBaseUrl()`
- ✅ Removed duplicate helper functions

## Testing Deployment

### 1. Local Test (with Railway backend):
```bash
cd frontend
npm run dev
# Frontend: http://localhost:3000
# Backend: https://astonachikw-production.up.railway.app
```

### 2. Build Test (simulating Railway):
```bash
cd frontend
$env:NEXT_PUBLIC_BACKEND_URL="https://astonachikw-production.up.railway.app"
npm run build
```

### 3. Verify Backend Connectivity:
```bash
curl https://astonachikw-production.up.railway.app/health
# Response: {"status":"ok"}

curl https://astonachikw-production.up.railway.app
# Response: {"name":"AstroCycle API","status":"online","health":"/health","docs":"/docs","api_prefixes":["/api","/v1"]}
```

## Troubleshooting

### Issue: Frontend shows JSON instead of web interface
**Solution:** You're accessing the backend URL directly. Access the frontend URL instead.

### Issue: API calls fail after deployment
**Solution:** Check environment variables in Railway dashboard:
1. Verify `NEXT_PUBLIC_BACKEND_URL` is set correctly
2. Ensure backend is running: `https://astonachikw-production.up.railway.app/health`

### Issue: Build fails on Railway
**Solution:**
1. Check Railway logs for errors
2. Verify Node.js version compatibility (requires Node 20+)
3. Ensure all dependencies are in `package.json`

## Local Development vs Railway Deployment

### Local Development (`.env.local`):
```bash
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### Railway Deployment (Railway environment variables):
```bash
NEXT_PUBLIC_BACKEND_URL=https://astonachikw-production.up.railway.app
NEXT_PUBLIC_API_URL=https://astonachikw-production.up.railway.app
```

## Git Ignore Configuration

The following files are excluded from Git:
- `*.env` (includes `.env.local`, `.env.railway`)
- `node_modules/`
- `.next/`
- `.venv/`
- `*.log`

## Final Verification Checklist

- [x] Frontend builds successfully with Railway environment variables
- [x] All API calls use `getApiBaseUrl()` helper
- [x] No hard-coded URLs remain in frontend code
- [x] Backend is online and accessible
- [x] Environment variables are properly configured
- [x] Docker configuration is correct
- [x] Railway configuration file exists

## Support

If issues persist:
1. Check Railway deployment logs
2. Verify backend connectivity
3. Test locally with Railway backend URL
4. Review environment variable configuration

**Deployment Status:** ✅ **READY FOR RAILWAY DEPLOYMENT**