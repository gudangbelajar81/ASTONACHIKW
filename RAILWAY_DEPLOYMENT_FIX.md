# 🚂 Railway Deployment Fix Guide

## ❌ Masalah yang Ditemukan

Berdasarkan screenshot, API backend menunjukkan status "online" tetapi aplikasi tidak dapat diakses dengan benar. Berikut adalah masalah yang ditemukan:

### 1. **Backend Dockerfile Tidak Konsisten**
- `backend/Dockerfile` menggunakan CMD yang berbeda dengan `railway.toml`
- Ini menyebabkan startup script tidak berjalan dengan benar
- **SUDAH DIPERBAIKI** ✅

### 2. **Environment Variables Mungkin Tidak Lengkap**
- Frontend perlu tahu URL backend
- Backend perlu database connection yang benar

### 3. **Tidak Ada Preview Lokal**
- Tidak ada cara mudah untuk test sebelum push
- **SUDAH DIPERBAIKI** dengan `preview_local.ps1` ✅

---

## ✅ Solusi & Langkah Perbaikan

### LANGKAH 1: Verifikasi File yang Sudah Diperbaiki

File berikut sudah diperbaiki:
- ✅ `backend/Dockerfile` - CMD sekarang menggunakan `python -m backend.scripts.start`
- ✅ `preview_local.ps1` - Script untuk preview lokal

### LANGKAH 2: Setup Railway Environment Variables

#### Untuk Backend Service:
```bash
# Database (Railway akan auto-inject ini jika Anda link Postgres service)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Security
SECRET_KEY=<generate-random-string-minimal-32-karakter>

# Frontend URL (ganti dengan URL Railway frontend Anda)
FRONTEND_URL=https://your-frontend.up.railway.app

# Backend URL (akan auto-set oleh Railway)
BACKEND_URL=${{RAILWAY_PUBLIC_DOMAIN}}

# AI Provider Keys (opsional, tapi disarankan)
AI_PROVIDER_ORDER=openai,gemini,deepseek,xai
OPENAI_API_KEY=<your-key>
GEMINI_API_KEY=<your-key>
DEEPSEEK_API_KEY=<your-key>
XAI_API_KEY=<your-key>

# Swiss Ephemeris Path
SWISSEPH_PATH=./ephemeris
```

#### Untuk Frontend Service:
```bash
# Backend URL (ganti dengan URL Railway backend Anda)
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

### LANGKAH 3: Verifikasi Railway Service Configuration

#### Backend Service:
1. **Root Directory**: `/backend` atau kosong (tergantung struktur)
2. **Build Command**: Otomatis dari Dockerfile
3. **Start Command**: `python -m backend.scripts.start` (dari railway.toml)
4. **Port**: Railway akan auto-detect port 8000

#### Frontend Service:
1. **Root Directory**: `/frontend` atau kosong
2. **Build Command**: `npm run build`
3. **Start Command**: `npm run start`
4. **Port**: Railway akan auto-detect port 3000

### LANGKAH 4: Deploy Ulang

```bash
# 1. Commit perubahan
git add .
git commit -m "fix: update backend Dockerfile CMD for Railway deployment"

# 2. Push ke Railway
git push origin main

# 3. Monitor deployment di Railway dashboard
# Cek logs untuk memastikan tidak ada error
```

---

## 🔍 Cara Cek Deployment Berhasil

### 1. Cek Backend Health
```bash
curl https://your-backend.up.railway.app/health
# Expected: {"status":"ok"}
```

### 2. Cek Backend Root
```bash
curl https://your-backend.up.railway.app/
# Expected: {"name":"AstroCycle API","status":"online",...}
```

### 3. Cek API Docs
Buka di browser: `https://your-backend.up.railway.app/docs`

### 4. Cek Frontend
Buka di browser: `https://your-frontend.up.railway.app`

---

## 🖥️ Preview Lokal Sebelum Push (BARU!)

Sekarang Anda bisa preview aplikasi secara lokal sebelum push:

```powershell
# Jalankan preview
.\preview_local.ps1
```

Script ini akan:
1. ✅ Cek Docker berjalan
2. ✅ Stop container lama
3. ✅ Build dan start semua services
4. ✅ Tunggu sampai ready
5. ✅ Buka browser otomatis ke:
   - Frontend: http://localhost:3000
   - Backend API Docs: http://localhost:8000/docs

**Untuk stop preview:**
```powershell
docker-compose down
```

---

## 🐛 Troubleshooting

### Backend Tidak Start
**Cek logs di Railway:**
```
# Kemungkinan masalah:
1. DATABASE_URL tidak diset
2. Migration gagal
3. Port sudah digunakan
```

**Solusi:**
- Pastikan Postgres service sudah di-link
- Pastikan DATABASE_URL variable reference benar: `${{Postgres.DATABASE_URL}}`

### Frontend Tidak Bisa Connect ke Backend
**Cek:**
1. NEXT_PUBLIC_API_URL sudah diset di frontend service
2. CORS settings di backend (`backend/app/main.py`) sudah include frontend URL
3. Backend benar-benar online (cek /health endpoint)

**Solusi:**
- Update FRONTEND_URL di backend environment variables
- Redeploy kedua services

### Database Connection Error
**Error:** `Railway database is not configured`

**Solusi:**
1. Buat Postgres service di Railway
2. Link Postgres service ke Backend service
3. Add variable reference: `DATABASE_URL=${{Postgres.DATABASE_URL}}`

---

## 📋 Checklist Deployment

Sebelum push, pastikan:

- [ ] ✅ Backend Dockerfile sudah diperbaiki
- [ ] Environment variables sudah diset di Railway
- [ ] Database service sudah di-link
- [ ] Frontend URL sudah diset di backend
- [ ] Backend URL sudah diset di frontend
- [ ] Test lokal dengan `.\preview_local.ps1`
- [ ] Commit dan push perubahan
- [ ] Monitor deployment logs di Railway
- [ ] Test endpoint /health dan /docs
- [ ] Test frontend bisa connect ke backend

---

## 🎯 Workflow Baru untuk Update

```bash
# 1. Buat perubahan di code
# ... edit files ...

# 2. Preview lokal
.\preview_local.ps1

# 3. Test di browser
# - http://localhost:3000 (frontend)
# - http://localhost:8000/docs (backend)

# 4. Jika OK, commit dan push
git add .
git commit -m "feat: your changes"
git push origin main

# 5. Monitor di Railway dashboard
# Tunggu deployment selesai dan test production URL
```

---

## 📞 Bantuan Lebih Lanjut

Jika masih ada masalah:

1. **Cek Railway Logs**: Klik service → Deployments → View Logs
2. **Cek Build Logs**: Pastikan build berhasil tanpa error
3. **Cek Runtime Logs**: Lihat error saat aplikasi running
4. **Test Lokal**: Gunakan `preview_local.ps1` untuk debug

---

**Dibuat:** 8 Juni 2026  
**Status:** ✅ Backend Dockerfile Fixed | ✅ Preview Script Created
