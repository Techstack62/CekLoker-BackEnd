# CekLoker Backend API

Backend API untuk aplikasi **CekLoker**, platform yang membantu pengguna mendeteksi lowongan pekerjaan (loker) palsu atau asli menggunakan OCR dan analisis AI.

Proyek ini dibangun menggunakan arsitektur modular (Clean Architecture) dengan teknologi modern berbasis asinkron.

---

## Tech Stack

| Kategori | Teknologi |
|---|---|
| Web Framework | FastAPI (Python 3.10+) |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (Async + `asyncpg`) |
| Migrations | Alembic |
| Validation & Config | Pydantic v2 & Pydantic Settings |
| Authentication | JWT (`python-jose` + `passlib` Bcrypt) |
| OCR | EasyOCR + Pillow + NumPy |
| Async File I/O | aiofiles |

---

## Fitur

### 🔐 Autentikasi
- **Register** — Daftar akun baru, password di-hash dengan Bcrypt.
- **Login** — Autentikasi dan mendapatkan JWT Access Token.

### 🔍 Cek Loker (Deteksi Scam)
- Upload gambar pamflet lowongan kerja (PNG/JPG, maks 10 MB).
- **OCR** otomatis mengekstrak informasi: nama loker, jenis pekerjaan, perusahaan, email, nomor telepon, gaji, deskripsi, dll.
- **Scam Analysis** (saat ini menggunakan mock AI) mengembalikan:
  - `scam_percentage` — persentase potensi scam (0–100%)
  - `scam_category` — kategori: Aman / Mencurigakan / Berpotensi Scam / Scam
  - `scam_reason` — alasan deteksi scam
- Hasil tersimpan ke **riwayat pribadi** masing-masing user.

### 📋 Riwayat Pengecekan
- Lihat semua riwayat cek loker milik akun sendiri (paginated).
- Lihat detail spesifik berdasarkan ID (hanya bisa diakses oleh pemiliknya).

### 👤 Profile User
- **Lihat Profile** — Lihat data profile user yang sedang login.
- **Edit Profile** — Update nama lengkap.
- **Upload Gambar Profile** — Upload atau ganti foto profile (PNG/JPG, maks 5 MB).
- **Lihat Gambar Profile** — Ambil gambar profile user.
- **Hapus Akun** — Hapus akun beserta semua data terkait (riwayat pengecekan loker). Tindakan ini **tidak dapat dibatalkan**.

---

## Struktur Project

```
app/
├── api/
│   ├── deps.py                  # Dependency injection (auth, db session)
│   └── v1/
│       ├── api.py               # Router utama API v1
│       └── endpoints/
│           ├── auth.py          # Endpoint autentikasi
│           ├── jobs.py          # Endpoint cek loker & riwayat
│           └── profile.py       # Endpoint profile user
├── core/
│   ├── config.py                # Konfigurasi environment variables
│   ├── database.py              # Koneksi async database
│   └── security.py             # JWT & hashing utilities
├── models/
│   ├── base.py                  # SQLAlchemy Base
│   ├── user.py                  # Model User
│   └── loker_check.py          # Model LokerCheck (hasil cek loker)
├── schemas/
│   ├── token.py                 # Schema JWT token
│   ├── user.py                  # Schema request/response user
│   └── loker.py                 # Schema request/response cek loker
├── services/
│   ├── ocr_service.py           # OCR extraction & parsing
│   └── scam_analysis_service.py # Scam analysis (mock AI — modular)
└── main.py                      # Entry point FastAPI app

uploads/
├── loker/                       # Gambar pamflet yang diupload user
└── profile/                      # Gambar profile user

alembic/                         # Migrasi database
```

---

## Prasyarat (Prerequisites)

- Python 3.10+
- PostgreSQL Server

---

## Setup (Local Development)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Techstack62/CekLoker-BackEnd.git
cd CekLoker-BackEnd

python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / Mac
# source venv/bin/activate
```

### 2. Install Dependensi
```bash
pip install -r requirements.txt
```

> **Catatan:** EasyOCR akan mengunduh model OCR-nya pada pertama kali dijalankan (~100 MB). Pastikan koneksi internet tersedia.

### 3. Konfigurasi Environment Variables
Salin `.env.example` menjadi `.env` lalu sesuaikan:
```bash
cp .env.example .env
```

Isi variabel berikut di `.env`:
```env
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@localhost:5432/<DB_NAME>
SECRET_KEY=<random-secret-key-minimal-32-karakter>
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DB_ECHO=false
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

> `SECRET_KEY` wajib minimal 32 karakter. `DB_ECHO=true` hanya disarankan saat debugging lokal karena akan menampilkan query SQL ke log.

### 4. Setup Database & Migrasi
```bash
alembic upgrade head
```

### 5. Jalankan Server
```bash
uvicorn app.main:app --reload
```

Server berjalan di `http://localhost:8000`.

---

## Dokumentasi API

Setelah server berjalan, akses dokumentasi interaktif di:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Endpoint API

### Auth (`/api/v1/auth`)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/register` | Daftar akun baru | ❌ |
| `POST` | `/login` | Login & dapatkan JWT token | ❌ |

### Jobs (`/api/v1/jobs`)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/check` | Upload gambar pamflet → OCR → analisis scam | ✅ |
| `GET` | `/history` | Riwayat cek loker milik user (paginated) | ✅ |
| `GET` | `/history/{check_id}` | Detail satu riwayat pengecekan | ✅ |
| `GET` | `/history/{check_id}/image` | Ambil gambar pamflet dari riwayat milik user | ✅ |

### Profile (`/api/v1/profile`)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/profile` | Lihat data profile user | ✅ |
| `PUT` | `/profile` | Edit nama lengkap | ✅ |
| `POST` | `/profile/image` | Upload atau ganti gambar profile | ✅ |
| `GET` | `/profile/image` | Lihat gambar profile | ✅ |
| `DELETE` | `/profile` | Hapus akun dan semua data terkait | ✅ |

> Endpoint bertanda ✅ memerlukan header `Authorization: Bearer <token>`.

---

## Catatan Pengembangan

### Keamanan

- **Validasi File Upload**: Semua file upload divalidasi berdasarkan tipe konten dan ekstensi. File yang bukan gambar valid akan ditolak.
- **Proteksi Endpoint**: Semua endpoint profile memerlukan autentikasi JWT. User hanya bisa mengakses dan memodifikasi data miliknya sendiri.
- **Cleanup Otomatis**: Gambar profile lama secara otomatis dihapus saat user mengupload gambar baru.
- **Cascade Delete**: Saat akun dihapus, semua data terkait (riwayat pengecekan loker) juga ikut dihapus.

### Mock AI Model
Analisis scam saat ini menggunakan **mock implementation** berbasis keyword matching. Modul ini dirancang secara modular di [`app/services/scam_analysis_service.py`](app/services/scam_analysis_service.py) — cukup ganti body fungsi `analyze_scam()` ketika model AI yang sesungguhnya sudah siap, tanpa perlu mengubah kode lain.

### Penyimpanan Gambar
Gambar yang diupload disimpan secara lokal di folder `uploads/` dengan nama file UUID:

- **Gambar Pamflet Loker**: `uploads/loker/`
- **Gambar Profile**: `uploads/profile/`

File upload asli tidak ter-push ke GitHub (`.gitignore`), tetapi folder tetap dipertahankan dengan `.gitkeep`.

Untuk menampilkan gambar, gunakan endpoint aman yang telah disediakan:

```http
# Gambar Pamflet Loker
GET /api/v1/jobs/history/{check_id}/image
Authorization: Bearer <token>

# Gambar Profile
GET /api/v1/profile/image
Authorization: Bearer <token>
```

Endpoint tersebut memastikan hanya pemilik yang dapat mengakses gambar. Untuk production, disarankan menggunakan object storage seperti AWS S3, Google Cloud Storage, atau Supabase Storage.