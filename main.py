"""
Facebook Group/Page Business Scraper
=====================================
Script otomatisasi untuk mengekstrak data usaha dari Grup/Halaman Facebook
"Pojok Bangkep" berdasarkan daftar kata kunci dari file eksternal.

Penggunaan:
    python main.py          -> Menu interaktif
    python main.py --setup  -> Langsung setup sesi login
    python main.py --run    -> Langsung mulai scraping
"""

import os
import re
import sys
import json
import time
import random
import urllib.parse
import pandas as pd
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Muat variabel dari file .env (jika ada)
load_dotenv()

# ==========================================
# KONFIGURASI TARGET
# ==========================================
TARGET_TYPE = "account"  # "group" atau "account"
TARGET_ID_GROUP = "787234888711411"
TARGET_ID_ACCOUNT = "100082853270304"

# Kredensial diambil dari file .env (lihat .env.example)
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASS = os.getenv("FB_PASS", "")

# ==========================================
# VARIABEL SISTEM
# ==========================================
STATE_FILE = "storage_state.json"
KEYWORD_FILE = "Keyword Data Usaha.txt"
OUTPUT_DIR = "output"
run_time = time.strftime("%Y%m%d_%H%M%S")
CSV_FILE = os.path.join(OUTPUT_DIR, f"listing_usaha_bangkep_{run_time}.csv")
PROGRESS_FILE = "scroll_progress.json"

# Delay konfigurasi
SCROLL_DELAY_MIN = 2.0   # detik antar scroll
SCROLL_DELAY_MAX = 4.0
KEYWORD_DELAY_MIN = 5.0  # detik antar keyword
KEYWORD_DELAY_MAX = 10.0


def get_base_url():
    """Menentukan Base URL berdasarkan tipe target yang dipilih."""
    if TARGET_TYPE == "group":
        return f"https://www.facebook.com/groups/{TARGET_ID_GROUP}/search/?q="
    else:
        return f"https://www.facebook.com/profile/{TARGET_ID_ACCOUNT}/search/?q="


# ==========================================
# PROGRESS MANAGEMENT (RESUME SUPPORT)
# ==========================================
def load_progress():
    """Memuat progress scroll dari file JSON."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    """Menyimpan progress scroll ke file JSON."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


# ==========================================
# TAHAP 1: SESSION MANAGEMENT
# ==========================================
def setup_session():
    """
    Load storage_state.json jika ada.
    Jika tidak ada, buka browser untuk user login manual (60 detik),
    lalu simpan sesinya.
    """
    with sync_playwright() as p:
        if os.path.exists(STATE_FILE):
            print(f"[INFO] File '{STATE_FILE}' sudah ada.")
            print("[INFO] Memverifikasi sesi tersimpan...")

            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state=STATE_FILE)
            page = context.new_page()
            page.goto("https://www.facebook.com")
            time.sleep(8)
            browser.close()
            print("[SUCCESS] Sesi tersimpan masih valid.\n")

        else:
            print(f"[INFO] File '{STATE_FILE}' TIDAK ditemukan.")
            print("[INFO] Membuka browser untuk login manual...\n")

            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.facebook.com")

            print("=" * 56)
            print("  SILAKAN LOGIN MANUAL KE FACEBOOK DI BROWSER SEKARANG")
            if FB_EMAIL:
                print(f"  Email : {FB_EMAIL}")
            else:
                print("  Email : (atur di file .env)")
            print("  Waktu : 60 detik sebelum sesi disimpan otomatis")
            print("=" * 56)

            try:
                for sisa in range(60, 0, -1):
                    print(f"\r  Sisa waktu: {sisa} detik ", end="", flush=True)
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[INFO] Countdown dihentikan manual oleh user.")

            print("\n\n[INFO] Menyimpan state (cookies/session)...")
            context.storage_state(path=STATE_FILE)
            print(f"[SUCCESS] Sesi berhasil disimpan ke '{STATE_FILE}'.\n")
            browser.close()


# ==========================================
# TAHAP 2: BACA KEYWORD
# ==========================================
def load_keywords():
    """Membaca file keyword baris per baris, bersihkan whitespace."""
    if not os.path.exists(KEYWORD_FILE):
        print(f"[ERROR] File '{KEYWORD_FILE}' tidak ditemukan!")
        print(f"[INFO]  Buat file '{KEYWORD_FILE}' berisi daftar keyword (satu per baris).")
        sys.exit(1)

    with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    if not keywords:
        print(f"[ERROR] File '{KEYWORD_FILE}' kosong!")
        sys.exit(1)

    print(f"[INFO] Berhasil memuat {len(keywords)} keyword dari '{KEYWORD_FILE}'.")
    return keywords


# ==========================================
# TAHAP 3: HELPER FUNCTIONS (EKSTRAKSI FIELD)
# ==========================================
def extract_phone(text):
    """
    Mengekstrak nomor telepon dari teks postingan.
    Mendukung format: 08xx, +62xx, 62xx, wa.me/xxxx
    """
    if not text:
        return "Tidak Ditemukan"

    patterns = [
        # wa.me/08xxxx atau wa.me/62xxxx
        r'wa\.me/(\+?[\d\-\s]{8,15})',
        # Format Indonesia: 08xx-xxxx-xxxx
        r'(0[89]\d[\d\-\s]{7,14})',
        # Format internasional: +62xxx
        r'(\+62[\d\-\s]{8,14})',
        # Format tanpa +: 62xxx (minimal 10 digit)
        r'(?<!\d)(62[89]\d[\d\-\s]{7,12})(?!\d)',
        # WhatsApp/WA diikuti nomor
        r'(?:WA|WhatsApp|Whatsapp|whatsapp|wa)\s*[:\-]?\s*([\d\+][\d\-\s]{8,15})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(1).strip()
            # Bersihkan format
            phone = re.sub(r'[\s\-]', '', phone)
            if len(phone) >= 10:
                return phone

    return "Tidak Ditemukan"


def extract_location(text, context_location=None):
    """
    Mengekstrak lokasi dari teks postingan atau data konteks Facebook.
    """
    # Prioritaskan lokasi dari metadata Facebook (context_layout)
    if context_location:
        return context_location

    if not text:
        return "Tidak Ditemukan"

    # Pola lokasi umum Indonesia (urutan = prioritas)
    location_patterns = [
        # Nama tempat spesifik Bangkep (paling akurat)
        r'((?:Salakan|Banggai Kepulauan|Banggai|Bangkep|Liang|Peleng|Bokan|Bulagi|Buko|Tinangkung|Totikum|Peling|Sulawesi Tengah)[^\n,]{0,40})',
        # Jl. / Jalan
        r'((?:Jl\.|Jalan|Jalur)\s+[^\n,]{5,60})',
        # Kelurahan/Kecamatan/Desa
        r'((?:Kel\.|Kelurahan|Kec\.|Kecamatan|Desa)\s+[^\n,]{3,40})',
        # "lokasi/alamat/tempat:" diikuti teks (keyword eksplisit, bukan "di" yang terlalu umum)
        r'(?:lokasi|alamat|tempat|t4)\s*[:\-]\s*([A-Z][^\n,\.]{3,60})',
        # "di <Nama Tempat Proper Noun>" — hanya jika diikuti kata yang dimulai huruf kapital
        # dan bukan kata umum seperti "di warung", "di dalam", "di sini"
        r'\bdi\s+((?:Jl\.|Jalan|Desa|Kel\.|Kec\.)\s+[^\n,]{3,60})',
        r'\bin\s+(Salakan|Banggai[^\n,]{0,40}|Bangkep[^\n,]{0,40})',
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            # Bersihkan trailing whitespace/punctuation
            loc = re.sub(r'[\s\.\,]+$', '', loc)
            if len(loc) >= 3:
                return loc

    return "Tidak Ditemukan"


def extract_business_name(text, keyword=""):
    """
    Mengekstrak nama usaha dari teks postingan.
    Strategi: cari pola "Warung <Nama Proper>", "RM <Nama>", dll.
    Jika tidak ditemukan nama spesifik, gunakan keyword + tipe usaha.
    """
    if not text:
        return "Tidak Teridentifikasi"

    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]

    # Kata-kata umum yang BUKAN nama usaha (filter negatif)
    non_name_words = {
        'sudah', 'sudh', 'so', 'buka', 'bkn', 'iyye', 'yee', 'dah', 'lagi',
        'mau', 'akan', 'ini', 'itu', 'nya', 'yg', 'yang', 'dan', 'juga',
        'saya', 'kami', 'kita', 'hari', 'besok', 'nanti', 'pagi', 'siang',
        'malam', 'mulai', 'tutup', 'sekarang', 'lama', 'baru', 'masih',
    }

    # Pola nama usaha umum — HARUS diikuti oleh proper noun (huruf kapital)
    business_type_words = (
        r'(?:Warung|RM|Rumah\s+Makan|Toko|Cafe|Kafe|Coffee\s+Shop|'
        r'Kedai|Bengkel|Salon|Laundry|Apotek|Kios|Depot|Kantin|Catering|'
        r'Gerai|Resto|Restoran|Bakso|Soto|Martabak|Gudang|CV|UD)'
    )
    business_patterns = [
        # "Warung <Nama Proper>": tipe usaha + nama yang dimulai huruf kapital
        rf'({business_type_words}\s+[A-Z][A-Za-z\s\'\"\.]{1,40})',
        # Nama usaha angka: "Warung 2 Putri", "RM 99"
        rf'({business_type_words}\s+\d+\s+[A-Z][A-Za-z\s]{{1,30}})',
        # Nama dengan format "Usaha: <nama>" atau "Nama Toko: <nama>"
        r'(?:usaha|bisnis|jualan|nama\s+(?:toko|warung|usaha))\s*[:\-]\s*([A-Za-z][^\n]{3,40})',
    ]

    for pattern in business_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Bersihkan trailing whitespace/emoji/punctuation
            name = re.sub(r'[\s\.\,\!\?]+$', '', name)
            name = re.sub(r'[^\w\s\'\.\-]', '', name).strip()
            
            # Cek apakah kata setelah tipe usaha bukan kata umum
            parts = name.split()
            if len(parts) >= 2:
                follow_word = parts[1].lower()
                if follow_word in non_name_words:
                    continue  # Skip — ini bukan nama usaha
            
            if len(name) >= 3:
                return name

    # Fallback 1: cari pola "<keyword> <nama>" di teks (case-insensitive)
    # contoh: "warung ibu ngadiem", "warung makan 2 putri"
    if keyword:
        kw_lower = keyword.lower()
        # Cari di setiap baris
        for line in lines:
            line_lower = line.lower()
            if kw_lower in line_lower:
                kw_pos = line_lower.find(kw_lower)
                after_kw = line[kw_pos + len(keyword):].strip()
                
                if not after_kw or len(after_kw) < 2:
                    continue
                
                # Ambil kata-kata setelah keyword
                after_words = after_kw.split()
                first_word = after_words[0].lower() if after_words else ""
                
                # Jika kata pertama setelah keyword bukan kata umum, ini mungkin nama usaha
                if first_word and first_word not in non_name_words:
                    # Ambil sampai 5 kata sebagai nama usaha
                    name_words = []
                    for w in after_words[:5]:
                        w_clean = re.sub(r'[^\w]', '', w)
                        if w_clean.lower() in non_name_words or not w_clean:
                            break
                        name_words.append(w_clean)
                    
                    if name_words:
                        candidate = f"{keyword.title()} {' '.join(name_words)}"
                        if len(candidate) >= 5:
                            return candidate

    return "Tidak Teridentifikasi"




# ==========================================
# TAHAP 4: EKSTRAKSI DATA DARI JSON FACEBOOK
# ==========================================
def extract_posts_from_json(page_html):
    """
    Mengekstrak data postingan dari JSON yang di-embed Facebook di tag <script>.

    Facebook menyimpan semua data di tag:
      <script type="application/json" data-sjs="" data-processed="1">
    
    Data JSON berisi objek "story" dengan struktur:
    - message.text : teks postingan
    - actors[].name : nama pembuat
    - actors[].url : URL profil pembuat
    - post_id : ID postingan
    - permalink_url / wwwURL : URL postingan
    - comet_sections.context_layout : metadata (waktu, lokasi, dll.)
    """
    results = []

    # Ekstrak semua blok script JSON dengan data-sjs
    script_blocks = re.findall(
        r'<script[^>]*type="application/json"[^>]*data-sjs[^>]*>(.*?)</script>',
        page_html,
        re.DOTALL
    )

    if not script_blocks:
        print("  [WARN] Tidak menemukan blok data JSON Facebook.")
        return results

    print(f"  [INFO] Ditemukan {len(script_blocks)} blok data JSON.")

    for block in script_blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue

        # Cari objek story/postingan di dalam JSON
        stories = _find_story_objects(data)
        
        for story in stories:
            post = _extract_post_data(story)
            if post:
                results.append(post)

    # Deduplikasi berdasarkan post_id 
    seen_ids = set()
    unique = []
    for post in results:
        # Gunakan kombinasi post_id + pesan sebagai key
        dedup_key = f"{post.get('_post_id', '')}:{post.get('Deskripsi_Usaha', '')[:50]}"
        if dedup_key not in seen_ids:
            seen_ids.add(dedup_key)
            unique.append(post)

    print(f"  [INFO] Ditemukan {len(results)} post total, {len(unique)} unik setelah deduplikasi.")
    return unique


def _find_story_objects(obj, depth=0):
    """
    Rekursif mencari objek story/postingan di dalam nested JSON Facebook.
    
    Sebuah "story" valid memiliki:
    - key "message" (dict dengan "text")
    - key "actors" (list)
    - key "post_id"
    """
    stories = []
    if depth > 40:
        return stories

    if isinstance(obj, dict):
        has_message = (
            "message" in obj
            and isinstance(obj.get("message"), dict)
            and "text" in obj.get("message", {})
        )
        has_actors = "actors" in obj and isinstance(obj.get("actors"), list)
        has_post_id = "post_id" in obj

        # Story utama: punya message + actors + post_id
        if has_message and has_actors and has_post_id:
            msg_text = obj["message"].get("text", "")
            # Hanya ambil story yang punya teks bermakna
            if msg_text and len(msg_text.strip()) > 10:
                stories.append(obj)

        for val in obj.values():
            stories.extend(_find_story_objects(val, depth + 1))

    elif isinstance(obj, list):
        for item in obj:
            stories.extend(_find_story_objects(item, depth + 1))

    return stories


def _find_key_recursive(obj, target_key, depth=0):
    """Mencari value dari key tertentu secara rekursif di nested dict/list."""
    results = []
    if depth > 20:
        return results
    if isinstance(obj, dict):
        if target_key in obj:
            results.append(obj[target_key])
        for v in obj.values():
            results.extend(_find_key_recursive(v, target_key, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_find_key_recursive(item, target_key, depth + 1))
    return results


def _extract_location_from_story(story):
    """Mengekstrak lokasi dari context_layout atau attached_story."""
    # Coba cari dari context_layout (biasanya mengandung info tempat)
    context = story.get("comet_sections", {}).get("context_layout", {})
    if context:
        context_str = json.dumps(context, ensure_ascii=False)
        # Cari nama tempat di context
        place_matches = re.findall(r'"name"\s*:\s*"([^"]+)"', context_str)
        for place in place_matches:
            # Filter nama tempat yang relevan (bukan nama user)
            if any(kw in place.lower() for kw in [
                'salakan', 'banggai', 'bangkep', 'peleng', 'liang', 'sulawesi',
                'bokan', 'bulagi', 'buko', 'tinangkung', 'totikum', 'peling',
                'indonesia', 'kecamatan', 'kelurahan', 'desa'
            ]):
                return place

    # Coba dari to (tagged location)
    to_list = story.get("to", [])
    if isinstance(to_list, list):
        for item in to_list:
            if isinstance(item, dict) and item.get("__typename") == "Page":
                return item.get("name", "")

    return None


def _extract_post_data(story):
    """Mengekstrak field data bisnis dari satu objek story."""
    try:
        # --- TEKS POSTINGAN ---
        msg_text = story.get("message", {}).get("text", "")
        if not msg_text or len(msg_text.strip()) < 10:
            return None

        # --- PEMILIK AKUN ---
        actors = story.get("actors", [])
        pemilik = "Tidak Diketahui"
        profil_url = ""
        if actors and isinstance(actors[0], dict):
            pemilik = actors[0].get("name", "Tidak Diketahui")
            profil_url = actors[0].get("url", "")

        # --- URL POSTINGAN ---
        # Coba permalink_url dulu, lalu wwwURL, lalu generate dari profil+post_id
        url_postingan = story.get("permalink_url", "")
        if not url_postingan:
            url_postingan = story.get("wwwURL", "")
        if not url_postingan and profil_url and story.get("post_id"):
            url_postingan = f"{profil_url}/posts/{story['post_id']}"
        if not url_postingan:
            url_postingan = "Tidak Tersedia"
        # Bersihkan backslash dari JSON encoding
        url_postingan = url_postingan.replace("\\", "")

        # --- LOKASI ---
        context_loc = _extract_location_from_story(story)
        lokasi = extract_location(msg_text, context_loc)

        # --- NOMOR TELEPON ---
        nomor_telepon = extract_phone(msg_text)

        # --- DESKRIPSI USAHA (maks 500 karakter) ---
        deskripsi = msg_text.strip()
        if len(deskripsi) > 500:
            deskripsi = deskripsi[:497] + "..."

        # --- POST ID (internal, untuk deduplikasi) ---
        post_id = story.get("post_id", "")

        return {
            "Pemilik_Akun": pemilik,
            "Nomor_Telepon": nomor_telepon,
            "Deskripsi_Usaha": deskripsi,
            "Lokasi": lokasi,
            "URL_Postingan": url_postingan,
            "_post_id": post_id,  # Internal, akan dihapus sebelum export
        }

    except Exception as e:
        print(f"  [ERROR] Gagal mengekstrak post: {e}")
        return None


def extract_posts_from_page(page):
    """
    Wrapper utama: ambil HTML halaman, lalu parse JSON.
    Juga menyertakan fallback via DOM jika JSON gagal.
    """
    # Strategi utama: Parse dari embedded JSON
    try:
        page_html = page.content()
        results = extract_posts_from_json(page_html)
        if results:
            return results
    except Exception as e:
        print(f"  [WARN] JSON extraction gagal: {e}")

    # Fallback: DOM-based extraction (versi perbaikan)
    print("  [INFO] Mencoba fallback: DOM-based extraction...")
    return _fallback_dom_extraction(page)


def _fallback_dom_extraction(page):
    """
    Fallback: ekstraksi via DOM menggunakan JavaScript evaluation.
    Lebih reliable daripada inner_text() karena mengakses React fiber data.
    """
    results = []

    try:
        # Gunakan JavaScript untuk mengekstrak teks bersih dari dir="auto" divs
        posts_data = page.evaluate("""
            () => {
                const feed = document.querySelector('div[role="feed"]');
                if (!feed) return [];
                
                const posts = [];
                const children = feed.querySelectorAll(':scope > div');
                
                for (const child of children) {
                    // Ambil semua elemen teks dengan dir="auto" (konten postingan)
                    const textDivs = child.querySelectorAll('div[dir="auto"]');
                    const texts = [];
                    for (const td of textDivs) {
                        const t = td.textContent.trim();
                        // Filter teks sampah (terlalu pendek atau "Facebook")
                        if (t && t.length > 3 && t !== 'Facebook' && !t.match(/^[a-z0-9]$/i)) {
                            texts.push(t);
                        }
                    }
                    
                    if (texts.length === 0) continue;
                    
                    // Ambil semua link
                    const links = child.querySelectorAll('a[href]');
                    let postUrl = '';
                    let authorName = '';
                    let authorUrl = '';
                    
                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        const text = link.textContent.trim();
                        
                        // Post URL
                        if (href.includes('/posts/') || href.includes('story_fbid') || href.includes('/permalink/')) {
                            postUrl = href.startsWith('/') ? 'https://www.facebook.com' + href : href;
                        }
                        
                        // Author (biasanya link pertama dengan teks non-kosong yang mengarah ke profil)
                        if (!authorName && text && text.length > 2 && text !== 'Facebook' &&
                            (href.includes('facebook.com/') || href.startsWith('/')) &&
                            !href.includes('/posts/') && !href.includes('story_fbid')) {
                            authorName = text;
                            authorUrl = href.startsWith('/') ? 'https://www.facebook.com' + href : href;
                        }
                    }
                    
                    if (texts.length > 0) {
                        posts.push({
                            fullText: texts.join('\\n'),
                            author: authorName || 'Tidak Diketahui',
                            authorUrl: authorUrl,
                            postUrl: postUrl || 'Tidak Tersedia'
                        });
                    }
                }
                
                return posts;
            }
        """)

        for post in posts_data:
            full_text = post.get("fullText", "")
            if not full_text or len(full_text.strip()) < 10:
                continue

            deskripsi = full_text.strip()
            if len(deskripsi) > 500:
                deskripsi = deskripsi[:497] + "..."

            results.append({
                "Pemilik_Akun": post.get("author", "Tidak Diketahui"),
                "Nomor_Telepon": extract_phone(full_text),
                "Deskripsi_Usaha": deskripsi,
                "Lokasi": extract_location(full_text),
                "URL_Postingan": post.get("postUrl", "Tidak Tersedia"),
                "_post_id": "",
            })

    except Exception as e:
        print(f"  [ERROR] DOM fallback gagal: {e}")

    return results


# ==========================================
# TAHAP 5: EXPORT CSV
# ==========================================
CSV_COLUMNS = [
    "Keyword_Pencarian",
    "Nama_Usaha",
    "Pemilik_Akun",
    "Nomor_Telepon",
    "Lokasi",
    "URL_Postingan",
]


def save_to_csv(data_list, keyword):
    """
    Simpan hasil ke CSV secara append.
    Setiap batch keyword langsung disimpan agar data tidak hilang jika crash.
    """
    if not data_list:
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Tambahkan kolom Keyword dan Nama_Usaha, hapus kolom internal
    for item in data_list:
        item["Keyword_Pencarian"] = keyword
        item["Nama_Usaha"] = extract_business_name(
            item.get("Deskripsi_Usaha", ""), keyword
        )
        # Hapus kolom internal
        item.pop("_post_id", None)

    df = pd.DataFrame(data_list)

    # Pastikan urutan kolom benar
    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = "Tidak Ditemukan"
    df = df[CSV_COLUMNS]

    file_exists = os.path.isfile(CSV_FILE)
    df.to_csv(CSV_FILE, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
    print(f"  [SAVED] {len(data_list)} record disimpan ke '{CSV_FILE}'.")


# ==========================================
# TAHAP 6: SCRAPING UTAMA
# ==========================================
def run_scraping():
    """
    Fungsi utama scraping:
    1. Load sesi
    2. Baca keyword
    3. Tanya user berapa kali scroll
    4. Loop: navigasi URL -> scroll (dengan resume) -> ekstrak -> simpan CSV
    """
    # Pastikan sesi sudah ada
    if not os.path.exists(STATE_FILE):
        print(f"[ERROR] File sesi '{STATE_FILE}' belum ada!")
        print("[INFO]  Jalankan setup sesi terlebih dahulu (pilih opsi 1).\n")
        return

    keywords = load_keywords()
    base_url = get_base_url()
    progress = load_progress()

    print(f"\n[INFO] Target  : {TARGET_TYPE.upper()} -> "
          f"{TARGET_ID_GROUP if TARGET_TYPE == 'group' else TARGET_ID_ACCOUNT}")
    print(f"[INFO] Keywords: {len(keywords)} kata kunci")
    print(f"[INFO] Output  : {CSV_FILE}")

    # Buat file CSV kosong dengan header agar file tetap muncul walau 0 data
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(CSV_FILE):
        df_empty = pd.DataFrame(columns=CSV_COLUMNS)
        df_empty.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

    # --- Tampilkan progress yang sudah ada ---
    if progress:
        print(f"\n[INFO] Progress sebelumnya ditemukan ({PROGRESS_FILE}):")
        for kw, info in progress.items():
            print(f"       - '{kw}': sudah scroll {info.get('last_scroll', 0)}x")
    
    # --- Input jumlah scroll dari user ---
    print("\n" + "-" * 56)
    print("  PENGATURAN SCROLL")
    print("-" * 56)
    print("  Masukkan jumlah scroll yang ingin dilakukan per keyword.")
    print("  Script akan MELANJUTKAN dari posisi scroll terakhir")
    print("  jika keyword tersebut pernah di-scrape sebelumnya.")
    print("  (Contoh: input 50, sebelumnya sudah 100 -> scroll dari 100 ke 150)")
    print("-" * 56)
    
    while True:
        scroll_input = input("\n  Jumlah scroll per keyword: ").strip()
        try:
            scroll_count = int(scroll_input)
            if scroll_count < 1:
                print("  [ERROR] Minimal 1 scroll.")
                continue
            break
        except ValueError:
            print("  [ERROR] Masukkan angka yang valid.")
    
    print(f"\n[INFO] Setiap keyword akan di-scroll {scroll_count}x (ditambahkan ke progress sebelumnya).\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        total_extracted = 0

        for i, keyword in enumerate(keywords):
            print("=" * 60)
            print(f"[{i+1}/{len(keywords)}] Keyword: '{keyword}'")

            # Cek progress sebelumnya untuk keyword ini
            prev_scroll = progress.get(keyword, {}).get("last_scroll", 0)
            if prev_scroll > 0:
                print(f"  [RESUME] Melanjutkan dari scroll ke-{prev_scroll}")
            print("=" * 60)

            # Navigasi ke URL pencarian
            encoded_kw = urllib.parse.quote(keyword)
            search_url = base_url + encoded_kw
            print(f"  [NAV] {search_url}")

            try:
                page.goto(search_url, timeout=30000)
            except Exception as e:
                print(f"  [ERROR] Gagal membuka halaman: {e}")
                print(f"  [SKIP] Melewati keyword '{keyword}'.\n")
                continue

            # Tunggu halaman dimuat
            time.sleep(random.uniform(4, 6))

            # --- Klik "See more" / "Selengkapnya" jika ada ---
            # Ini penting untuk mendapatkan teks lengkap
            try:
                see_more_btns = page.query_selector_all('div[role="button"]')
                for btn in see_more_btns:
                    btn_text = btn.inner_text().strip()
                    if btn_text in ["See more", "Selengkapnya", "See More"]:
                        try:
                            btn.click()
                            time.sleep(0.5)
                        except Exception:
                            pass
            except Exception:
                pass

            # --- SCROLL PHASE ---
            # Jika ada progress sebelumnya, scroll cepat ke posisi lama dulu
            total_scroll_target = prev_scroll + scroll_count

            if prev_scroll > 0:
                print(f"  [SKIP-SCROLL] Menggulir cepat melewati {prev_scroll} scroll sebelumnya...")
                for s in range(prev_scroll):
                    page.mouse.wheel(0, random.randint(1500, 2500))
                    # Scroll cepat untuk catch-up (delay lebih pendek)
                    time.sleep(random.uniform(0.8, 1.5))
                    if (s + 1) % 20 == 0:
                        print(f"    - Catch-up scroll {s+1}/{prev_scroll}...")
                print(f"  [OK] Berhasil melewati posisi scroll lama.")
                time.sleep(random.uniform(2, 3))

            # Scroll baru
            print(f"  [SCROLL] Melakukan {scroll_count}x scroll baru (posisi {prev_scroll+1} -> {total_scroll_target})...")

            for s in range(scroll_count):
                page.mouse.wheel(0, random.randint(1500, 2500))
                delay = random.uniform(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX)
                current_pos = prev_scroll + s + 1
                if (s + 1) % 10 == 0 or (s + 1) == scroll_count:
                    print(f"    - Scroll {s+1}/{scroll_count} (posisi absolut: {current_pos}) (jeda {delay:.1f}s)")
                time.sleep(delay)

            # Tunggu rendering selesai setelah scroll
            time.sleep(random.uniform(2, 3))

            # Update progress
            progress[keyword] = {"last_scroll": total_scroll_target}
            save_progress(progress)

            # Ekstraksi data
            print("  [EXTRACT] Mengekstrak data postingan...")
            data = extract_posts_from_page(page)

            if data:
                save_to_csv(data, keyword)
                total_extracted += len(data)
                print(f"  [OK] {len(data)} postingan berhasil diekstrak.")
            else:
                print(f"  [WARN] Tidak ada data ditemukan untuk keyword '{keyword}'.")

            # Jeda antar keyword (anti rate-limit)
            if i < len(keywords) - 1:
                wait = random.uniform(KEYWORD_DELAY_MIN, KEYWORD_DELAY_MAX)
                print(f"  [WAIT] Jeda {wait:.1f}s sebelum keyword berikutnya...\n")
                time.sleep(wait)

        print("\n" + "=" * 60)
        print(f"[SELESAI] Scraping selesai. Total data terkumpul: {total_extracted} record.")
        print(f"[OUTPUT]  File: {CSV_FILE}")
        print(f"[PROGRESS] Tersimpan di: {PROGRESS_FILE}")
        print("=" * 60)

        browser.close()


def reset_progress():
    """Menghapus file progress untuk mulai dari awal."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print(f"[INFO] File progress '{PROGRESS_FILE}' telah dihapus.")
    else:
        print(f"[INFO] File progress '{PROGRESS_FILE}' tidak ditemukan, tidak ada yang dihapus.")


# ==========================================
# MENU UTAMA
# ==========================================
def main():
    """Menu interaktif untuk memilih aksi."""
    # Cek argumen command line
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            setup_session()
            return
        elif sys.argv[1] == "--run":
            run_scraping()
            return

    progress = load_progress()

    print("\n" + "=" * 56)
    print("  FACEBOOK BUSINESS SCRAPER - BANGKEP SE2026")
    print("=" * 56)
    print(f"  Target  : {TARGET_TYPE.upper()} -> "
          f"{TARGET_ID_GROUP if TARGET_TYPE == 'group' else TARGET_ID_ACCOUNT}")
    print(f"  Sesi    : {'ADA' if os.path.exists(STATE_FILE) else 'BELUM ADA'}")
    print(f"  Keyword : {KEYWORD_FILE}")
    print(f"  Output  : {CSV_FILE}")
    print(f"  Progress: {len(progress)} keyword sudah pernah di-scrape" if progress else "  Progress: Belum ada")
    print("=" * 56)
    print()
    print("  [1] Setup Sesi (Login manual 60 detik)")
    print("  [2] Mulai Scraping (input jumlah scroll)")
    print("  [3] Reset Progress (mulai dari awal)")
    print("  [4] Keluar")
    print()

    pilihan = input("  Pilih menu (1/2/3/4): ").strip()

    if pilihan == "1":
        print()
        setup_session()
    elif pilihan == "2":
        print()
        run_scraping()
    elif pilihan == "3":
        print()
        reset_progress()
    elif pilihan == "4":
        print("\n[EXIT] Sampai jumpa.\n")
    else:
        print("\n[ERROR] Pilihan tidak valid.\n")


if __name__ == "__main__":
    main()