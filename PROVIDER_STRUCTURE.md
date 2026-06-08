# Struktur Data Provider - ASTONACHIKW

## Ringkasan Perubahan

Aplikasi telah diperbarui untuk memisahkan data provider berdasarkan kategori yang lebih spesifik dan terorganisir dengan baik.

## Kategori Provider

### 1. **Pusat Data IDX** (Bursa Efek Indonesia)
Provider khusus untuk data pasar Indonesia:

- **IDX Bandar Accumulation** - Analisis akumulasi dan distribusi bandar
  - Contoh endpoint: `https://indonesia-stock-exchange-idx.p.rapidapi.com/api/analysis/bandar/accumulation/{ticker}?days={days}`
  
- **IDX Broker Summary** - Broker net buy/sell dan top broker activity
  - Contoh endpoint: `https://indonesia-stock-exchange-idx.p.rapidapi.com/api/broker/summary/{ticker}`
  
- **IDX Foreign Flow** - Foreign net buy/sell dan aliran dana asing
  - Contoh endpoint: `https://indonesia-stock-exchange-idx.p.rapidapi.com/api/foreign/flow/{ticker}`
  
- **IDX Order Book / Running Trade** - Order book imbalance, big lot, dan running trade realtime
  - Contoh endpoint: `https://indonesia-stock-exchange-idx.p.rapidapi.com/api/orderbook/{ticker}`

### 2. **Data Global Market**
Provider untuk data pasar global:

- **MarketFlow Global Data** - Data pasar global dari MarketFlow API (US, Asia, Europe)
  - Contoh endpoint: `https://marketflow.p.rapidapi.com/api/market/{symbol}`

### 3. **Data Macro Economy**
Provider untuk data makro ekonomi:

- **Kalender Ekonomi** - Kalender ekonomi global dan Indonesia (GDP, inflasi, suku bunga)
  - Contoh endpoint: `https://economic-calendar.p.rapidapi.com/api/events`
  
- **BI Rate & Macro Indonesia** - BI Rate, inflasi, USD/IDR, dan indikator makro Indonesia
  - Contoh endpoint: `https://indonesia-macro.p.rapidapi.com/api/indicators`

### 4. **Data Berita & Sentiment**
Provider untuk berita ekonomi:

- **Berita Ekonomi RSS** - Feed berita ekonomi dan pasar dari berbagai sumber RSS
  - Contoh endpoint: `https://news-api.p.rapidapi.com/api/rss/finance`

### 5. **Custom Provider**
Provider custom yang formatnya bisa dipetakan sesuai kebutuhan.

## Poin Penting

### ✅ Yang Benar
1. **Setiap provider memiliki endpoint yang spesifik** sesuai fungsinya
2. **Gunakan template variable** `{ticker}` dan `{days}` untuk endpoint yang dinamis
3. **Pisahkan provider berdasarkan kategori** untuk kemudahan pengelolaan
4. **Jangan gunakan endpoint yang sama** untuk provider yang berbeda

### ❌ Yang Salah
1. ❌ Menggunakan endpoint `bandar/accumulation` untuk Foreign Flow
2. ❌ Menggunakan endpoint `bandar/accumulation` untuk Order Book
3. ❌ Mencampur data IDX dengan data Global Market di satu tab
4. ❌ Menaruh Kalender Ekonomi di tab Pusat Data IDX

## Struktur File

### `frontend/lib/apiKeys.ts`
- Definisi tipe data provider dengan kategori
- Default provider configuration dengan placeholder endpoint
- Fungsi read/write untuk localStorage

### `frontend/app/settings/page.tsx`
- UI untuk mengelola provider berdasarkan kategori
- Tab terpisah untuk setiap kategori (IDX, Global, Macro, News)
- Filter provider berdasarkan kategori

## Cara Penggunaan

1. **Buka Settings** → Pilih tab kategori yang sesuai
2. **Isi Endpoint API** → Gunakan contoh endpoint sebagai referensi
3. **Isi API Key** → Masukkan API key dari provider (misalnya RapidAPI)
4. **Aktifkan Provider** → Centang checkbox untuk mengaktifkan
5. **Cek Status** → Klik tombol "Cek Status" untuk memverifikasi

## Keamanan

⚠️ **PENTING**: Jangan share screenshot yang menampilkan API key Anda. Jika API key terekspos, segera regenerate di dashboard provider (RapidAPI, dll).

## Migrasi Data Lama

Data provider lama akan otomatis dimigrasikan ke struktur baru dengan kategori default. Namun, Anda perlu:
1. Memverifikasi endpoint setiap provider
2. Memastikan endpoint sesuai dengan fungsi provider
3. Update API key jika diperlukan

---

**Terakhir diupdate**: 8 Juni 2026
**Versi**: 2.0
