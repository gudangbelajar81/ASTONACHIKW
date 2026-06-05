# AstroCycle

AstroCycle adalah monorepo SaaS untuk platform cycle forecasting dengan backend FastAPI, PostgreSQL, dan dashboard Next.js.

## Arsitektur

- Frontend: Next.js 15 + TypeScript
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Deployment: Railway / Docker
- Charting: TradingView Lightweight Charts

## Struktur proyek

- `/frontend` — aplikasi Next.js untuk login dan dashboard
- `/backend` — API FastAPI, JWT auth, model user/subscription
- `/backend/alembic` — konfigurasi dan migrasi database
- `railway.json` — Railway deployment manifest

## Fitur

- JWT authentication (signup, login, current user)
- User model dan subscription model
- PostgreSQL async connection
- Alembic migration scaffolding
- Dark theme dashboard dengan sidebar
- TradingView lightweight chart demo
- Astronomy ingestion engine dengan Swiss Ephemeris
- API endpoint `GET /api/planets`
- Cycle analysis engine dengan perhitungan kosinus sudut planet
- API endpoint `GET /api/cycle` untuk analisis cycle antar planet
- Composite cycle engine dengan weighted combinations
- API endpoint `POST /api/composite` untuk weighted composite cycles
- Smoothing support (7, 30, 60 days)
- Future projection dengan polynomial fitting
- Cycle scanner dengan correlation, lead/lag, dan accuracy metrics
- API endpoint `GET /api/scanner` untuk finding best planetary combinations
- Turning point detection dengan local extrema dan cycle reversals
- API endpoint `GET /api/turning-points` untuk major tops/bottoms
- AI market analyst dengan OpenAI GPT-4
- API endpoint `POST /api/analyst` untuk human-readable analysis

## Persiapan lokal

### 0. Jalankan PostgreSQL lokal (opsional — Docker)

Jika Anda belum punya PostgreSQL lokal, jalankan container Docker berikut:

```powershell
docker-compose up -d
```

Ini akan menyiapkan PostgreSQL pada `localhost:5432` dengan kredensial default yang ada di `docker-compose.yml`.

### 1. Setup environment

Gunakan Python 3.12 untuk backend lokal. Dependency backend dipin agar konsisten dengan `backend/Dockerfile`; Python yang lebih baru dapat memaksa beberapa package scientific dibuild dari source.
Gunakan Node.js 20 atau lebih baru untuk frontend.

```powershell
cd c:\Users\Administrator\Desktop\ASTONACHIKW
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install backend dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```powershell
cd ..\frontend
npm install
```

Jika npm di Windows gagal dengan `UNABLE_TO_VERIFY_LEAF_SIGNATURE`, gunakan cache lokal workspace:

```powershell
npm install --no-audit --no-fund --strict-ssl=false --cache .\.npm-cache
```

### 4. Konfigurasi environment

Salin contoh env:

```powershell
copy .env.example .env
```

Lalu sesuaikan `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL`, `BACKEND_URL`, dan `OPENAI_API_KEY`.

**Untuk AI Analyst feature:**
1. Dapatkan OpenAI API key dari https://platform.openai.com/api-keys
2. Set `OPENAI_API_KEY=sk-your-key` di `.env`
3. Pastikan akun memiliki akses ke GPT-4 model


### 5. Jalankan migrasi database

```powershell
cd backend
alembic upgrade head
```

Atau dari folder root:

```powershell
alembic -c backend\alembic.ini upgrade head
```

### 5b. Seed data sample (market + ephemeris)

Gunakan seed script untuk mengisi data contoh (mis. AAPL 1 tahun terakhir):

```powershell
cd backend
.\run_seed.ps1 -Symbol AAPL -Days 365
```

Setelah seed selesai, panggilan endpoint seperti `/api/planets` dan `/api/cycle` akan mengembalikan data nyata.

### 5c. Headless smoke test (seed + quick API checks)

Untuk menjalankan seed lalu melakukan pemeriksaan cepat otomatis pada backend, jalankan:

```powershell
cd backend
.\run_seed_and_smoke.ps1
```

Script akan: melakukan seed, menjalankan backend di background, memanggil `/health`, `/api/planets`, dan `/api/cycle` lalu mematikan server.

### 6. Jalankan aplikasi

Backend:

```powershell
cd c:\Users\Administrator\Desktop\ASTONACHIKW
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

Lalu buka `http://localhost:3000`.

### Mode demo lokal tanpa backend

Frontend tetap bisa dicoba saat backend/PostgreSQL belum aktif. Dashboard akan memakai data demo lokal, dan login bisa memakai:

```text
Email: demo@astrocycle.local
Password: demo12345
```

Untuk menjalankan hasil build lokal di port 3001 dari root:

```powershell
npm --prefix frontend run build
$env:PORT=3001
node server.js
```

### Quick: Jalankan seluruh stack lokal (satu perintah)

Script `run_all_local.ps1` mengorkestrasi:
- Docker (Postgres), virtualenv, instal dependensi
- Migrasi database (alembic)
- Seed data contoh (AAPL, 365 hari)
- Men-start backend dan frontend sebagai proses latar

Jalankan ini dari folder repo root (PowerShell):

```powershell
.\run_all_local.ps1
```

Perhatian: skrip ini men-start proses background; catat PID yang ditampilkan untuk menghentikannya.

## API Documentation

### GET /api/planets

Fetch planetary positions untuk tanggal tertentu.

Query parameters:
- `date` (optional): YYYY-MM-DD format. Jika tidak ada, menggunakan tanggal terbaru di database.

Response:
```json
{
  "date": "2025-01-01",
  "sun": 123.45,
  "moon": 210.33,
  "mercury": 87.22,
  "venus": 98.23,
  "mars": 132.41,
  "jupiter": 212.11,
  "saturn": 45.19
}
```

### GET /api/cycle

Analisis cycle antara dua planet.

Query parameters:
- `planet_a` (required): First planet (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn)
- `planet_b` (required): Second planet
- `start_date` (required): YYYY-MM-DD format
- `end_date` (required): YYYY-MM-DD format

Response:
```json
[
  {
    "date": "2025-01-01",
    "value": 0.45
  },
  {
    "date": "2025-01-02",
    "value": 0.67
  }
]
```

Cycle value dihitung menggunakan: `cos(radians(planet_a_longitude - planet_b_longitude))`

### POST /api/composite

Analisis weighted composite cycles dengan multiple planet combinations.

Request body:
```json
{
  "combinations": [
    {
      "planet_a": "Sun",
      "planet_b": "Venus",
      "weight": 1.0
    },
    {
      "planet_a": "Sun",
      "planet_b": "Jupiter",
      "weight": 0.8
    },
    {
      "planet_a": "Moon",
      "planet_b": "Saturn",
      "weight": 0.5
    }
  ],
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "smoothing_windows": [7, 30, 60],
  "project_days": 30
}
```

Response:
```json
[
  {
    "date": "2025-01-01",
    "value": 0.45,
    "smoothed_7d": 0.42,
    "smoothed_30d": 0.38,
    "smoothed_60d": 0.40,
    "projected": false
  },
  {
    "date": "2026-01-01",
    "value": 0.52,
    "smoothed_7d": null,
    "smoothed_30d": null,
    "smoothed_60d": null,
    "projected": true
  }
]
```

Features:
- Multiple weighted cycle combinations
- Weighted average calculation: `(w1*c1 + w2*c2 + w3*c3) / (w1 + w2 + w3)`
- Smoothing dengan rolling windows (7, 30, 60 days)
- Future projection dengan polynomial fitting (degree 2)
- Normalized values between -1 dan 1

### GET /api/scanner

Cycle scanner untuk menemukan kombinasi planet terbaik untuk market tertentu.

Query parameters:
- `ticker` (required): Market ticker (e.g., AAPL, ^JKSE, BTC-USD)
- `lookback_years` (optional, default=3): Jumlah tahun untuk lookback (1-20 years)

Response:
```json
{
  "ticker": "AAPL",
  "lookback_years": 3,
  "combinations_tested": 21,
  "top_combinations": [
    {
      "cycle": "Venus-Jupiter",
      "correlation": 0.63,
      "lag_days": 5,
      "accuracy": 0.68,
      "score": 0.654,
      "sample_count": 1000
    },
    {
      "cycle": "Moon-Venus",
      "correlation": 0.58,
      "lag_days": 3,
      "accuracy": 0.62,
      "score": 0.608,
      "sample_count": 1000
    }
  ]
}
```

Metrics:
- **correlation**: Pearson correlation antara cycle dan market returns
- **lag_days**: Optimal lag untuk predictive power (0-20 days)
- **accuracy**: Direction prediction accuracy (0-1)
- **score**: Weighted score = 0.6*|correlation| + 0.4*accuracy
- **sample_count**: Jumlah data points yang digunakan

### GET /api/turning-points

Detect major turning points (tops and bottoms) in market cycles.

Query parameters:
- `ticker` (required): Market ticker (e.g., AAPL, ^JKSE, BTC-USD)
- `lookback_days` (optional, default=90): Number of days to analyze (1-365)

Response:
```json
{
  "ticker": "AAPL",
  "lookback_days": 90,
  "turning_points": [
    {
      "date": "2026-05-18",
      "type": "BOTTOM",
      "strength": 88
    },
    {
      "date": "2026-05-25",
      "type": "TOP",
      "strength": 82
    }
  ],
  "total_detected": 2
}
```

Detection Rules:
- **Local Maxima**: Peak in cycle values within sliding window
- **Local Minima**: Trough in cycle values within sliding window
- **Cycle Reversals**: Sign changes in smoothed composite cycle
- **Strength Score** (0-100): Based on cycle magnitude, market volatility, and consistency

### POST /api/analyst

Generate AI-powered market analysis using OpenAI GPT-4.

Request body:
```json
{
  "ticker": "AAPL",
  "composite_cycle_data": [
    {"date": "2026-05-18", "value": 0.5},
    {"date": "2026-05-19", "value": 0.6}
  ],
  "turning_points": [
    {"date": "2026-05-18", "type": "BOTTOM", "strength": 88}
  ],
  "scanner_results": [
    {
      "cycle": "Venus-Jupiter",
      "correlation": 0.63,
      "lag_days": 5,
      "accuracy": 0.68,
      "score": 0.654
    }
  ]
}
```

Response:
```json
{
  "ticker": "AAPL",
  "summary": "The Venus-Jupiter cycle suggests a potential market bottom during the second half of May 2026.",
  "cycle_explanation": "The composite cycle is in positive territory with increasing momentum, indicating strong bullish conditions.",
  "turning_points_explanation": "Recent bottom at 2026-05-18 confirms cycle reversal with high strength score of 88, suggesting significant support level.",
  "scan_explanation": "Venus-Jupiter combination shows strongest correlation (0.63) with 5-day lead, making it the most reliable predictor for this market.",
  "outlook": "Expect continued upside momentum through June 2026 as cycle remains positive and turning point signals remain intact."
}
```

AI Analysis generates:
- **Summary**: Brief cycle state overview
- **Cycle Explanation**: Interpretation of composite cycle trend
- **Turning Points Explanation**: Analysis of detected tops/bottoms
- **Scanner Insights**: Strongest planetary combinations
- **Outlook**: Forward-looking market perspective

## Deployment Railway

Railway manifest `railway.json` sudah tersedia. Konfigurasikan environment:

- `DATABASE_URL`
- `SECRET_KEY`
- `FRONTEND_URL`
- `BACKEND_URL`

Backend service:

- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`

Frontend service:

- Build: `npm install`
- Start: `npm run build && npm run start`

## Catatan

- Pastikan `SECRET_KEY` menggunakan nilai acak yang kuat.
- `FRONTEND_URL` dan `BACKEND_URL` dipakai untuk CORS.
- Jika ingin menambahkan pipeline astrologi, letakkan logika di `backend/app/services`.
