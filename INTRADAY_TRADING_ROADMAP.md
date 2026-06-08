# Intraday Trading Center - Roadmap Implementasi

## 🎯 Visi
Mengubah AstroCycle dari tool analisis swing trading menjadi **asisten trading harian lengkap** yang membantu trader memilih saham, menunggu trigger, menghitung risiko, dan mengevaluasi hasil.

## 📊 Konsep Utama

### Perbedaan Swing vs Intraday
| Aspek | Swing Trading | Intraday Trading |
|-------|---------------|------------------|
| Timeframe | Daily, Weekly, Monthly | 15M, 1H, Daily |
| Holding Period | Beberapa hari - minggu | Beberapa jam - 1 hari |
| Fokus | Trend jangka menengah | Momentum harian |
| Entry | Setup multi-hari | Trigger intraday |
| Risk | 2-5% per trade | 0.5-1% per trade |
| Target | 10-30% | 2-5% per hari |

### Multi-Timeframe Hierarchy
```
Monthly/Weekly → Filter trend besar (jangan melawan)
       ↓
    Daily → Pilih kandidat watchlist
       ↓
     1H → Konfirmasi momentum intraday
       ↓
    15M → Timing entry/trigger
```

## 🏗️ Arsitektur Fitur Baru

### 1. Intraday Trading Center (Frontend)
**Lokasi**: `frontend/app/intraday/page.tsx`

**Sections**:
- Market Pulse
- Top Intraday Watchlist
- Entry Trigger Monitor
- Position Sizing Calculator
- Active Trade Tracker
- End-of-Day Review

### 2. Multi-Timeframe Engine (Backend)
**Lokasi**: `backend/app/services/intraday_engine.py`

**Fungsi**:
- Analisis 15M, 1H, Daily, Weekly, Monthly
- Scoring per timeframe
- Kombinasi multi-timeframe score
- Setup detection (breakout, pullback, continuation, reversal)

### 3. Pre-Market Scanner (Backend)
**Lokasi**: `backend/app/services/premarket_scanner.py`

**Output**:
- Top 10 Intraday Watchlist
- Top 10 Breakout Candidate
- Top 10 Pullback Candidate
- Top 10 Avoid / High Risk

### 4. Entry Trigger System (Backend)
**Lokasi**: `backend/app/services/trigger_monitor.py`

**Status**:
- WAIT
- READY
- TRIGGERED
- INVALID
- TAKE_PROFIT
- STOPPED

## 📋 Fase Implementasi

### Phase 1: Foundation (Week 1-2)
**Priority: HIGH**

#### Backend
- [ ] Buat `intraday_engine.py` untuk multi-timeframe analysis
- [ ] Implementasi scoring system per timeframe
- [ ] Buat endpoint `/api/intraday/market-pulse`
- [ ] Buat endpoint `/api/intraday/watchlist`
- [ ] Implementasi 4 setup detector:
  - Breakout Intraday
  - Pullback Buy
  - Continuation Momentum
  - Reversal Cepat

#### Frontend
- [ ] Buat halaman `/intraday`
- [ ] Implementasi Market Pulse component
- [ ] Implementasi Watchlist Table component
- [ ] Tambahkan menu "Intraday Trading" di Sidebar

#### Data
- [ ] Setup provider untuk data 15M/1H (Yahoo Finance API)
- [ ] Fallback mechanism jika data intraday tidak tersedia
- [ ] Cache strategy untuk data intraday

### Phase 2: Entry Trigger & Risk Management (Week 3-4)
**Priority: HIGH**

#### Backend
- [ ] Buat `trigger_monitor.py`
- [ ] Implementasi trigger detection logic
- [ ] Buat endpoint `/api/intraday/signal/{symbol}`
- [ ] Buat endpoint `/api/intraday/position-size`
- [ ] Implementasi risk management calculator

#### Frontend
- [ ] Entry Trigger Monitor component
- [ ] Position Sizing Calculator component
- [ ] Real-time status update (polling/websocket)
- [ ] Alert system untuk trigger

### Phase 3: Trade Tracking & Review (Week 5-6)
**Priority: MEDIUM**

#### Backend
- [ ] Buat `trade_tracker.py`
- [ ] Database schema untuk trade log
- [ ] Buat endpoint `/api/intraday/trades`
- [ ] Buat endpoint `/api/intraday/review`
- [ ] Performance analytics

#### Frontend
- [ ] Active Trade Tracker component
- [ ] End-of-Day Review component
- [ ] Performance charts
- [ ] Trade journal

### Phase 4: Advanced Features (Week 7-8)
**Priority: LOW**

#### Backend
- [ ] Pre-market scanner automation
- [ ] Sector rotation analysis
- [ ] Market regime detection
- [ ] Backtesting intraday strategies

#### Frontend
- [ ] Advanced filters
- [ ] Custom alerts
- [ ] Mobile-responsive design
- [ ] Export trade reports

## 🔧 Technical Specifications

### Intraday Score Components (0-100)

```python
INTRADAY_SCORE_WEIGHTS = {
    "daily_setup_quality": 0.25,      # 25%
    "1h_momentum": 0.20,               # 20%
    "15m_trigger": 0.20,               # 20%
    "volume_spike": 0.15,              # 15%
    "relative_strength_vs_ihsg": 0.10, # 10%
    "bandarmology_flow": 0.05,         # 5%
    "risk_reward": 0.05                # 5%
}
```

### Score Categories
- **80-100**: High Probability Intraday Setup
- **70-79**: Good Watch
- **60-69**: Wait Confirmation
- **50-59**: Weak
- **<50**: Avoid

### Setup Types

#### 1. Breakout Intraday
```python
{
    "type": "breakout_intraday",
    "criteria": {
        "daily": "near_resistance",
        "1h": "bullish",
        "15m": "breakout_confirmed",
        "volume": "spike > 1.5x",
        "distance_from_entry": "< 2%"
    }
}
```

#### 2. Pullback Buy
```python
{
    "type": "pullback_buy",
    "criteria": {
        "daily": "uptrend",
        "1h": "healthy_correction",
        "15m": "bounce_from_support",
        "stop_loss": "tight",
        "risk_reward": "> 1.5"
    }
}
```

#### 3. Continuation Momentum
```python
{
    "type": "continuation_momentum",
    "criteria": {
        "daily": "already_up",
        "volume": "strong",
        "distribution": "none",
        "15m": "higher_low"
    }
}
```

#### 4. Reversal Cepat
```python
{
    "type": "reversal_cepat",
    "criteria": {
        "daily": "at_support",
        "volume": "selling_weakening",
        "15m": "bullish_reversal",
        "risk": "small"
    }
}
```

### API Response Format

#### `/api/intraday/signal/{symbol}`
```json
{
  "symbol": "BBRI.JK",
  "mode": "intraday",
  "score": 82,
  "setup_type": "breakout_intraday",
  "status": "READY",
  "timeframes": {
    "monthly": {
      "score": 75,
      "trend": "bullish",
      "note": "Long-term uptrend intact"
    },
    "weekly": {
      "score": 78,
      "trend": "bullish",
      "note": "Weekly consolidation"
    },
    "daily": {
      "score": 76,
      "trend": "bullish",
      "setup": "near_breakout",
      "resistance": 5450,
      "support": 5300
    },
    "1h": {
      "score": 81,
      "trend": "bullish",
      "momentum": "strengthening",
      "ma20": 5420,
      "vwap": 5410
    },
    "15m": {
      "score": 86,
      "trigger": "breakout_confirmed",
      "volume_spike": true,
      "last_price": 5455,
      "breakout_level": 5450
    }
  },
  "trade_plan": {
    "entry_trigger": "break above 5450 with volume > 1.5x avg",
    "entry_zone": [5450, 5475],
    "stop_loss": 5350,
    "target_1": 5550,
    "target_2": 5650,
    "risk_reward": 2.1,
    "invalidation": "close 15m below 5350"
  },
  "risk": {
    "risk_level": "medium",
    "max_risk_per_trade": "1%",
    "suggested_position_size": "calculated_by_position_sizer",
    "avoid_if": [
      "IHSG breakdown",
      "volume breakout lemah",
      "harga gap up terlalu jauh"
    ]
  },
  "market_context": {
    "ihsg_trend": "bullish",
    "sector_strength": "banking_strong",
    "market_regime": "risk_on"
  },
  "timestamp": "2026-06-08T09:30:00+07:00",
  "data_quality": {
    "15m_available": true,
    "1h_available": true,
    "real_time": false,
    "delay_minutes": 15
  }
}
```

#### `/api/intraday/position-size`
```json
{
  "capital": 10000000,
  "risk_per_trade": 0.01,
  "risk_amount": 100000,
  "entry": 5450,
  "stop_loss": 5350,
  "risk_per_share": 100,
  "suggested_shares": 1000,
  "suggested_lot": 10,
  "position_value": 5450000,
  "position_percentage": 54.5,
  "warnings": [
    "Position size > 50% of capital - consider reducing"
  ]
}
```

#### `/api/intraday/market-pulse`
```json
{
  "timestamp": "2026-06-08T09:30:00+07:00",
  "ihsg": {
    "price": 7250,
    "change": 1.2,
    "trend": "bullish",
    "regime": "risk_on"
  },
  "lq45": {
    "change": 1.5,
    "trend": "bullish"
  },
  "sectors": {
    "strongest": [
      {"name": "Banking", "change": 2.1},
      {"name": "Technology", "change": 1.8},
      {"name": "Consumer", "change": 1.5}
    ],
    "weakest": [
      {"name": "Mining", "change": -0.8},
      {"name": "Property", "change": -0.5}
    ]
  },
  "forex": {
    "usd_idr": 15750,
    "change": -0.3
  },
  "market_breadth": {
    "advancing": 245,
    "declining": 180,
    "unchanged": 75,
    "ratio": 1.36
  }
}
```

## 🎨 UI/UX Design

### Intraday Trading Center Layout

```
┌─────────────────────────────────────────────────────┐
│  INTRADAY TRADING CENTER                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📊 MARKET PULSE                                    │
│  ┌──────────┬──────────┬──────────┬──────────┐    │
│  │ IHSG     │ LQ45     │ USD/IDR  │ Regime   │    │
│  │ +1.2%    │ +1.5%    │ 15,750   │ Risk-On  │    │
│  └──────────┴──────────┴──────────┴──────────┘    │
│                                                     │
│  🎯 TOP INTRADAY WATCHLIST                         │
│  ┌────────────────────────────────────────────┐    │
│  │ Ticker │ Score │ Setup │ Entry │ SL │ TP  │    │
│  ├────────────────────────────────────────────┤    │
│  │ BBRI   │  82   │ BRK   │ 5450  │5350│5550 │    │
│  │ BBCA   │  78   │ PUL   │ 9200  │9100│9350 │    │
│  │ TLKM   │  75   │ CON   │ 3850  │3800│3950 │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  ⚡ ENTRY TRIGGER MONITOR                          │
│  ┌────────────────────────────────────────────┐    │
│  │ BBRI.JK  │ READY    │ Wait breakout 5450   │    │
│  │ BBCA.JK  │ WAIT     │ Need 1H confirmation │    │
│  │ TLKM.JK  │ TRIGGERED│ Entry confirmed!     │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  💰 POSITION SIZING CALCULATOR                     │
│  📈 ACTIVE TRADES (2/3)                            │
│  📊 END-OF-DAY REVIEW                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 🔐 Risk Management Rules

### Hard Rules (Enforced by System)
1. **Risk per trade**: 0.5% - 1% modal
2. **Max active positions**: 2-3 saham
3. **Max daily loss**: 2-3% modal
4. **Min risk/reward**: 1.5
5. **No averaging down** pada losing position
6. **Stop loss wajib** untuk setiap trade

### Soft Rules (Warning Only)
1. Position size > 50% capital
2. Entry saat gap up > 3%
3. Entry tanpa volume confirmation
4. Trade melawan IHSG trend

## 📊 Data Provider Strategy

### Priority Order
1. **RapidAPI IDX** (jika tersedia) - Real-time/near real-time
2. **Yahoo Finance API** - Delayed 15-20 menit
3. **OHLC.dev** - Fallback
4. **Provider berbayar** - Future upgrade

### Data Requirements
- **15M candles**: Last 50 bars (12.5 jam trading)
- **1H candles**: Last 100 bars (100 jam = ~2 minggu)
- **Daily candles**: Last 200 bars (~10 bulan)
- **Weekly candles**: Last 52 bars (1 tahun)
- **Monthly candles**: Last 24 bars (2 tahun)

### Fallback Mode
Jika data 15M tidak tersedia:
- **Semi-Intraday Mode**: Daily + 1H only
- **Disclaimer**: "Data delayed / not real-time"
- **Adjusted scoring**: Fokus ke Daily + 1H saja

## 🧪 Testing Strategy

### Unit Tests
- [ ] Multi-timeframe scoring
- [ ] Setup detection logic
- [ ] Position sizing calculator
- [ ] Risk management rules

### Integration Tests
- [ ] API endpoints
- [ ] Data provider integration
- [ ] Database operations

### Manual Tests
- [ ] UI/UX flow
- [ ] Real market data
- [ ] Performance under load

## 📈 Success Metrics

### Technical Metrics
- API response time < 500ms
- Data refresh rate: 1-5 minutes
- System uptime > 99%

### Trading Metrics
- Win rate target: > 50%
- Average R:R: > 1.5
- Max drawdown: < 5%
- Sharpe ratio: > 1.0

## 🚀 Quick Start Implementation

### Step 1: Create Basic Structure
```bash
# Backend
mkdir -p backend/app/services/intraday
touch backend/app/services/intraday/__init__.py
touch backend/app/services/intraday/engine.py
touch backend/app/services/intraday/scanner.py
touch backend/app/services/intraday/trigger.py

# Frontend
mkdir -p frontend/app/intraday
touch frontend/app/intraday/page.tsx
mkdir -p frontend/components/intraday
```

### Step 2: Implement Core Engine
Start with `backend/app/services/intraday/engine.py`

### Step 3: Create API Endpoints
Add routes in `backend/app/api/v1/intraday.py`

### Step 4: Build Frontend
Create components in `frontend/components/intraday/`

## 📝 Notes

- **Jangan over-promise**: Jika data delayed, tampilkan disclaimer
- **Fokus pada risk management**: Lebih penting dari prediksi akurat
- **Keep it simple**: 4 setup saja dulu, jangan terlalu banyak
- **User education**: Sertakan tutorial cara pakai

---

**Status**: 🟡 Planning Phase
**Target Launch**: Phase 1 dalam 2 minggu
**Maintainer**: Development Team
**Last Updated**: 8 Juni 2026
