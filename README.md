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

## Fitur### 🔐 Autentikasi
- **Register** — Daftar akun baru, password di-hash dengan Bcrypt.
- **Login** — Autentikasi dan mendapatkan JWT Access Token.

### 🔍 Cek Loker (Deteksi Scam) - Two-Stage Workflow

Fitur cek loker menggunakan alur **dua tahap** yang memberikan kontrol penuh kepada user:

#### Stage 1: OCR & Review
- Upload gambar pamflet lowongan kerja (PNG/JPG, maks 10 MB).
- **OCR** otomatis mengekstrak informasi: nama loker, jenis pekerjaan, perusahaan, email, nomor telepon, gaji, deskripsi, dll.
- Hasil OCR ditampilkan untuk direview dan dikoreksi oleh user jika ada kesalahan.
- Data disimpan sebagai **draft** sebelum analisis.

#### Stage 2: Submit & Analisis
- User submit draft yang sudah dikoreksi untuk dilakukan analisis scam.
- **Scam Analysis** (saat ini menggunakan mock AI) mengembalikan:
  - `scam_percentage` — persentase potensi scam (0–100%)
  - `scam_category` — kategori: Aman / Mencurigakan / Berpotensi Scam / Scam
  - `scam_reason` — alasan deteksi scam
- Hasil tersimpan ke **riwayat pribadi** masing-masing user.

### 📋 Riwayat Pengecekan
- Lihat semua riwayat cek loker milik akun sendiri (paginated).
- Lihat detail spesifik berdasarkan ID (hanya bisa diakses oleh pemiliknya).

### 🌐 Community Sharing
- **Share ke Community** — User bisa mempublish hasil cek loker ke community feed.
- **Unshare** — User bisa menarik kembali hasil yang sudah dishare.
- **Anonymous Option** — User bisa memilih untuk dishare secara anonymous atau dengan nama.
- **Community Feed** — List semua hasil yang dishare (paginated, filterable).
- **Privacy by Default** — Hasil cek loker tidak otomatis dishare.

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
│           ├── jobs.py          # Endpoint cek loker & riwayat (two-stage)
│           ├── profile.py       # Endpoint profile user
│           └── community.py     # Endpoint community feed
├── core/
│   ├── config.py                # Konfigurasi environment variables
│   ├── database.py              # Koneksi async database
│   ├── security.py             # JWT & hashing utilities
│   ├── errors.py               # Error code constants
│   └── exceptions.py           # Custom exception classes
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

## Error Handling

Semua endpoint API menggunakan **standardized error response format** untuk konsistensi dan kemudahan debugging.

### Standard Error Response Format

```json
{
  "error": "ERROR_CODE",
  "message": "Pesan error dalam Bahasa Indonesia",
  "details": { ... },
  "timestamp": "2026-06-10T14:49:00Z"
}
```

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | GET, PUT, PATCH successful |
| 201 | Created | POST successful (resource created) |
| 204 | No Content | DELETE successful (no body response) |
| 400 | Bad Request | Invalid request format, malformed JSON |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but not authorized for this action |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Resource already exists, duplicate entry |
| 413 | Payload Too Large | File size exceeds limit |
| 415 | Unsupported Media Type | Content-Type not supported |
| 422 | Unprocessable Entity | Validation error (Pydantic validation failed) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

### Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|--------------|
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | No access to resource |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `BAD_REQUEST` | 400 | Invalid request |
| `VALIDATION_ERROR` | 422 | Data validation failed |
| `FILE_TOO_LARGE` | 413 | File size exceeds limit |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | File format not supported |
| `FILE_CORRUPTED` | 422 | Invalid or corrupted file |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |

### Example Error Responses

#### 401 Unauthorized
```json
{
  "error": "UNAUTHORIZED",
  "message": "Autentikasi diperlukan. Silakan login terlebih dahulu.",
  "details": null,
  "timestamp": "2026-06-10T14:49:00Z"
}
```

#### 404 Not Found
```json
{
  "error": "NOT_FOUND",
  "message": "Draft dengan ID 123 tidak ditemukan.",
  "details": {"resource_type": "Draft", "resource_id": "123"},
  "timestamp": "2026-06-10T14:49:00Z"
}
```

#### 422 Validation Error
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Validasi data gagal.",
  "details": {
    "field_errors": [
      {"field": "email", "message": "Format email tidak valid."}
    ]
  },
  "timestamp": "2026-06-10T14:49:00Z"
}
```

#### 500 Internal Server Error
```json
{
  "error": "INTERNAL_SERVER_ERROR",
  "message": "Terjadi kesalahan pada server. Silakan coba lagi nanti.",
  "details": null,
  "timestamp": "2026-06-10T14:49:00Z"
}
```

---

## Endpoint API

### Auth (`/api/v1/auth`)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/register` | Daftar akun baru | ❌ |
| `POST` | `/login` | Login & dapatkan JWT token | ❌ |

### Jobs (`/api/v1/jobs`) - Two-Stage Workflow

#### OCR & Draft Endpoints

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/ocr` | Upload gambar → OCR → return hasil untuk review | ✅ |
| `GET` | `/drafts` | List semua draft user (paginated) | ✅ |
| `GET` | `/drafts/{draft_id}` | Detail satu draft | ✅ |
| `PUT` | `/drafts/{draft_id}` | Update/edit hasil OCR draft | ✅ |
| `POST` | `/drafts/{draft_id}/submit` | Submit draft untuk analisis scam | ✅ |
| `DELETE` | `/drafts/{draft_id}` | Hapus draft | ✅ |

#### History & Sharing Endpoints

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/check` | ⚠️ **Deprecated** — Gunakan `/ocr` | ✅ |
| `GET` | `/history` | Riwayat cek loker yang sudah di-submit (paginated) | ✅ |
| `GET` | `/history/{check_id}` | Detail satu riwayat pengecekan | ✅ |
| `GET` | `/history/{check_id}/image` | Ambil gambar pamflet dari riwayat | ✅ |
| `POST` | `/history/{check_id}/share` | Share hasil ke community | ✅ |
| `DELETE` | `/history/{check_id}/share` | Unshare dari community | ✅ |

### Community (`/api/v1/community`)

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/` | Community feed (paginated, filterable) | ❌ |
| `GET` | `/{report_id}` | Detail satu report di community | ❌ |

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

## Setup (Local Development)

###1. Clone & Setup Virtual Environment
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

## Catatan Pengembangan

### Keamanan

- **Validasi File Upload**: 
  - Magic bytes validation (prevents file spoofing)
  - Chunked file reading dengan size limit (prevents DoS attacks)
  - Content-type validation
- **Rate Limiting**: 10 upload per menit per IP pada endpoint upload
- **Proteksi Endpoint**: Semua endpoint memerlukan autentikasi JWT
- **Authorization**: User hanya bisa mengakses dan memodifikasi data miliknya sendiri
- **Privacy di Community**: Data sensitif (email, phone) di-mask di community feed
- **Cleanup Otomatis**: Gambar lama secara otomatis dihapus saat upload baru
- **Cascade Delete**: Saat akun dihapus, semua data terkait ikut dihapus
- **Logging**: Security events di-log untuk monitoring
- **Consistent Error Handling**: Semua endpoint menggunakan standardized error format

### Privacy di Community Feed

Data yang dishare ke community sudah di-mask untuk melindungi privasi:
- **Email**: `us***@domain.com` (hanya 2 karakter pertama visible)
- **Phone**: `***1234` (hanya 4 karakter terakhir visible)

User bisa memilih untuk share secara anonymous atau dengan nama.

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