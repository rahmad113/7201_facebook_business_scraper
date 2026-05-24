# Buku Panduan Penggunaan Skrip Facebook Scraper
### BPS Kabupaten Banggai Kepulauan — Sensus Ekonomi 2026

---

## 1. Pendahuluan

Skrip ini dibuat untuk melakukan **ekstraksi otomatis data usaha** dari Grup Facebook "Pojok Bangkep" atau akun Facebook `pojok.bangkep`. Data yang dikumpulkan mencakup:

| Kolom | Keterangan |
|---|---|
| **Keyword_Pencarian** | Kata kunci yang digunakan saat pencarian |
| **Nama_Usaha** | Nama usaha yang teridentifikasi dari postingan |
| **Pemilik_Akun** | Nama akun Facebook pembuat postingan |
| **Nomor_Telepon** | Nomor telepon yang ditemukan dalam teks |
| **Deskripsi_Usaha** | Ringkasan isi postingan (maks 500 karakter) |
| **Lokasi** | Alamat/lokasi yang terdeteksi dari teks |
| **URL_Postingan** | Tautan langsung ke postingan sumber |

Data ini digunakan sebagai bahan **pra-listing** untuk kegiatan Sensus Ekonomi 2026 (SE 2026) di wilayah Kabupaten Banggai Kepulauan.

---

## 2. Persyaratan Sistem (Prerequisites)

| Komponen | Spesifikasi |
|---|---|
| Sistem Operasi | Windows 10/11 |
| Python | Versi **3.10** atau lebih baru |
| Koneksi Internet | Stabil (tanpa VPN) |
| RAM | Minimal 4 GB |
| Akun Facebook | Akun operasional yang sudah terverifikasi |

### Mengecek Versi Python
Buka **Command Prompt** atau **PowerShell**, ketik:
```powershell
python --version
```
Jika belum terinstal, unduh di [python.org/downloads](https://www.python.org/downloads/) dan **centang "Add Python to PATH"** saat instalasi.

---

## 3. Cara Instalasi (Deployment)

### Langkah 1: Buka Terminal
Buka **PowerShell** atau **Command Prompt**, lalu arahkan ke folder proyek:
```powershell
cd "C:\Users\Public\Public File\BPS\BPS BANGKEP\SE 2026\SCRAPING"
```

### Langkah 2: Buat Virtual Environment (Opsional, Disarankan)
```powershell
python -m venv venv
```
Aktifkan virtual environment:
```powershell
.\venv\Scripts\activate
```

### Langkah 3: Instal Library
```powershell
pip install -r requirements.txt
```

### Langkah 4: Instal Browser Playwright
```powershell
playwright install chromium
```

### Langkah 5: Siapkan Kredensial (.env)
Salin file template `.env.example` menjadi `.env`:
```powershell
copy .env.example .env
```
Buka file `.env` dengan Notepad, lalu isi email dan password Facebook Anda:
```
FB_EMAIL=email_anda@gmail.com
FB_PASS=password_anda
```
> **Penting:** File `.env` berisi informasi sensitif dan **tidak boleh dibagikan** atau di-upload ke GitHub. File ini sudah tercantum di `.gitignore`.

### Verifikasi Instalasi
Jalankan perintah berikut untuk memastikan semua terinstal:
```powershell
python -c "from playwright.sync_api import sync_playwright; import pandas; print('OK')"
```
Jika muncul `OK`, instalasi berhasil.

---

## 4. Konfigurasi Target

### 4.1 Mengatur Tipe Target
Buka file `main.py` menggunakan Notepad atau editor teks. Di bagian atas, cari blok konfigurasi:

```python
TARGET_TYPE = "group"              # Pilihan: "group" atau "account"
TARGET_ID_GROUP = "787234888711411" # ID Grup Facebook
TARGET_ID_ACCOUNT = "100082853270304" # Username akun/halaman
```

| Nilai `TARGET_TYPE` | Target Sasaran |
|---|---|
| `"group"` | Grup Facebook (menggunakan `TARGET_ID_GROUP`) |
| `"account"` | Halaman/Akun (menggunakan `TARGET_ID_ACCOUNT`) |

### 4.2 Mengatur Daftar Kata Kunci
Buka file **`Keyword Data Usaha.txt`** menggunakan Notepad. Isinya berupa satu kata kunci per baris:
```
warung
warung makan
rumah makan
cafe
coffee shop
...
```

> **Catatan:** Anda bebas menambah, mengurangi, atau mengubah urutan kata kunci sesuai kebutuhan. Setiap baris yang tidak kosong akan dijadikan satu sesi pencarian.

### 4.3 Konfigurasi Delay & Scroll
Jika diperlukan, Anda dapat menyesuaikan parameter berikut di `main.py`:

| Parameter | Default | Keterangan |
|---|---|---|
| `SCROLL_MIN` / `SCROLL_MAX` | 3 / 5 | Jumlah scroll per pencarian |
| `SCROLL_DELAY_MIN` / `SCROLL_DELAY_MAX` | 2.0 / 4.0 detik | Jeda antar scroll |
| `KEYWORD_DELAY_MIN` / `KEYWORD_DELAY_MAX` | 5.0 / 10.0 detik | Jeda antar perpindahan keyword |

---

## 5. Prosedur Penggunaan (SOP)

### Tahap 1: Setup Sesi (Login Manual)

Tahap ini **hanya perlu dilakukan sekali** untuk menyimpan cookies/session Facebook.

1. Pastikan terminal sudah berada di folder proyek dan virtual environment aktif.
2. Jalankan perintah:
   ```powershell
   python main.py
   ```
3. Akan muncul menu interaktif:
   ```
   ========================================================
     FACEBOOK BUSINESS SCRAPER - BANGKEP SE2026
   ========================================================
     Target : GROUP -> 787234888711411
     Sesi   : BELUM ADA
     Keyword: Keyword Data Usaha.txt
     Output : listing_usaha_bangkep.csv
   ========================================================

     [1] Setup Sesi (Login manual 60 detik)
     [2] Mulai Scraping
     [3] Keluar

     Pilih menu (1/2/3):
   ```
4. **Ketik `1`** dan tekan Enter.
5. Browser Chromium akan terbuka dan memuat halaman facebook.com.
6. **Segera login** menggunakan email dan password yang sudah disiapkan.
7. Selesaikan verifikasi 2FA jika diminta.
8. Tunggu hingga hitungan mundur 60 detik selesai.
9. Terminal akan menampilkan pesan `[SUCCESS] Sesi berhasil disimpan`.

> **Penting:** Setelah tahap ini, file `storage_state.json` akan tercipta. Anda **tidak perlu login ulang** selama file ini masih ada. Jika suatu saat sesi kadaluarsa, hapus file `storage_state.json` dan ulangi Tahap 1.

### Tahap 2: Mulai Scraping

1. Jalankan kembali:
   ```powershell
   python main.py
   ```
2. **Ketik `2`** dan tekan Enter.
3. Script akan secara otomatis:
   - Membuka browser dengan sesi tersimpan
   - Membaca daftar keyword dari `Keyword Data Usaha.txt`
   - Untuk setiap keyword: navigasi → scroll → ekstrak data → simpan ke CSV
   - Memberikan jeda acak antar keyword
4. **Jangan tutup browser** selama proses berjalan.
5. Tunggu hingga muncul pesan `[SELESAI] Scraping selesai`.

### Alternatif: Menggunakan Argumen Command Line
Anda juga bisa menjalankan langsung tanpa menu:
```powershell
python main.py --setup   # Langsung ke setup sesi
python main.py --run     # Langsung mulai scraping
```

---

## 6. Batasan & Keamanan (Safety Limits)

### ⚠️ Peringatan Penting

| Risiko | Penjelasan |
|---|---|
| **Rate Limit** | Facebook membatasi jumlah permintaan. Script sudah dilengkapi jeda otomatis (5-10 detik antar keyword). **Jangan mengubah delay menjadi lebih cepat.** |
| **Checkpoint Akun** | Jika Facebook mendeteksi aktivitas mencurigakan, akun bisa terkena checkpoint (diminta verifikasi). Gunakan akun operasional cadangan. |
| **Login Ganda** | Jangan login ke akun yang sama dari HP/perangkat lain saat script berjalan. |
| **Jumlah Keyword** | Dengan 87 keyword, estimasi waktu proses: **1-2 jam**. Jangan menjalankan ratusan keyword dalam satu sesi. |

### Praktik Terbaik
- Jalankan script di **jam non-sibuk** (pagi hari atau malam hari).
- Jika akun diminta checkpoint, **hentikan script** (Ctrl+C), tunggu beberapa jam, lalu lanjutkan.
- Buat cadangan file CSV secara berkala.
- Jangan menjalankan script lebih dari **2-3 kali per hari**.

---

## 7. Output Data

### File Output
  - **Nama file:** `output/listing_usaha_bangkep_YYYYMMDD_HHMMSS.csv` (dinamis menggunakan stempel waktu untuk mencegah tertindih)
- **Encoding:** UTF-8 with BOM (bisa dibuka langsung di Excel tanpa karakter rusak)
- **Mode:** Append (data baru ditambahkan di bawah data lama)

### Struktur Kolom CSV

| No | Kolom | Tipe | Contoh |
|---|---|---|---|
| 1 | `Keyword_Pencarian` | Teks | warung makan |
| 2 | `Nama_Usaha` | Teks | RM Padang Sederhana |
| 3 | `Pemilik_Akun` | Teks | Ahmad Rizal |
| 4 | `Nomor_Telepon` | Teks | 081234567890 |
| 5 | `Deskripsi_Usaha` | Teks | Menerima pesanan nasi box... |
| 6 | `Lokasi` | Teks | Jl. Merdeka No. 5, Banggai |
| 7 | `URL_Postingan` | URL | https://www.facebook.com/groups/... |

### Membuka di Excel
1. Buka aplikasi **Microsoft Excel**.
2. Klik **File → Open**, ubah filter ke "All Files".
3. Pilih file `listing_usaha_bangkep.csv`.
4. Pada dialog import, pilih **Delimited → Comma** → **Finish**.

### Catatan tentang Data
- Kolom `Nomor_Telepon` dan `Lokasi` bersifat **best-effort** — tidak semua postingan menyertakan informasi ini. Jika tidak ditemukan, akan terisi "Tidak Ditemukan".
- Kolom `Deskripsi_Usaha` dipotong maksimal 500 karakter untuk efisiensi penyimpanan.
- Data disimpan secara **append** per keyword. Jika script dihentikan di tengah jalan, data keyword yang sudah selesai tetap tersimpan aman.

---

## 8. Troubleshooting

| Masalah | Solusi |
|---|---|
| Browser tidak terbuka | Jalankan `playwright install chromium` ulang |
| Sesi kadaluarsa / redirect ke login | Hapus `storage_state.json`, ulangi Tahap 1 |
| Data kosong untuk semua keyword | Periksa apakah akun benar-benar sudah login (cek Tahap 1) |
| Error `ModuleNotFoundError` | Pastikan virtual environment aktif, jalankan `pip install -r requirements.txt` |
| Script berhenti tiba-tiba | Data yang sudah tersimpan aman di CSV. Jalankan ulang script — keyword yang sudah diproses akan muncul duplikat, bisa dibersihkan di Excel |
| Facebook minta checkpoint | Hentikan script, verifikasi akun manual, tunggu beberapa jam |

---

*Dokumen ini disiapkan oleh Tim IPDS BPS Kabupaten Banggai Kepulauan untuk keperluan internal Sensus Ekonomi 2026.*
