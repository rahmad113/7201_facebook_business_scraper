# Project Requirements: Facebook Group/Page Business Scraper

## 1. Deskripsi Proyek
Script otomatisasi Python untuk mengekstrak data postingan usaha dari dalam Grup atau Halaman Facebook spesifik ("Pojok Bangkep") berdasarkan daftar kata kunci dari file eksternal.

## 2. Tech Stack
- Bahasa: Python 3.10+
- Library Utama: `playwright` (sync/async).
- Library Pendukung: `pandas` (untuk export data), `urllib.parse` (untuk URL encoding).

## 3. Fitur Utama & Alur Sistem
1. **Session Management:** Load `storage_state.json`. Jika tidak ada, pause script untuk login manual.
2. **Keyword Injection:** - Script harus membaca file `Keyword Data Usaha.txt` baris per baris.
   - Bersihkan whitespace pada setiap keyword.
3. **Targeted URL Navigation:**
   - Lakukan perulangan (loop) untuk setiap keyword.
   - Format URL yang dituju: `https://www.facebook.com/groups/<TARGET_ID>/search/?q=<URL_ENCODED_KEYWORD>` (Siapkan variabel global `TARGET_ID` di awal script agar mudah diganti).
4. **Infinite Scroll & Ekstraksi:**
   - Setelah URL terbuka, lakukan scroll ke bawah 3-5 kali dengan delay acak (2-4 detik) untuk merender postingan.
   - Ekstrak elemen dari hasil pencarian: Nama Akun/Pembuat Postingan, Teks Postingan (untuk mengidentifikasi nama/alamat usaha), dan URL Postingan tersebut.
5. **Data Export:**
   - Simpan hasil secara *append* ke `listing_usaha_bangkep.csv` setiap kali satu keyword selesai dieksekusi (jangan menunggu semua keyword selesai untuk mencegah data hilang jika crash).

## 4. Constraint & Limitasi
- **WAJIB** ada jeda acak (5-10 detik) antara perpindahan pencarian keyword satu ke keyword lainnya agar terhindar dari *rate limit* Facebook.
- Gunakan error handling (`try-except`) yang kuat pada tahap ekstraksi elemen. Jika struktur HTML postingan tidak terbaca, catat sebagai "Data Tidak Lengkap" namun script harus tetap berjalan ke postingan/keyword berikutnya.

## 5. Sasaran scraping dan akun facebook
- https://www.facebook.com/pojok.bangkep
- https://www.facebook.com/groups/787234888711411
- ini link akun dan grup yang mau di scraping buatkan pilihannya dulu mau scraing akun pojok.bangkep atau grup.
- Kredensial Facebook disimpan di file `.env` (lihat `.env.example` untuk template).
- buatkan juga buku pedoman deploy dan pedoman penggunaannya