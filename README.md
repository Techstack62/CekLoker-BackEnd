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

## Fitur Utama

### 🔐 Autentikasi
- **Register** — Daftar akun baru, password di-hash dengan Bcrypt.
- **Login** — Autentikasi dan mendapatkan JWT Access Token.

### 🔍 Cek Loker (Deteksi Scam) - Two-Stage Workflow

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

### 4. Setup Database & Migrasi
```bash
alembic upgrade head
```

### 5. Jalankan Server
```bash
uvicorn app.main:app --reload
```

Server berjalan di `http://localhost:8000`.

## Menjalankan dengan Docker

Proyek ini juga dapat dijalankan menggunakan Docker untuk memudahkan deployment dan pengembangan.

### Prasyarat
- Docker dan Docker Compose terinstal di sistem Anda

### Langkah-langkah

1. **Konfigurasi Environment Variables**
   Salin `.env.example` menjadi `.env` dan sesuaikan nilainya:
   ```bash
   cp .env.example .env
   ```

2. **Bangun dan Jalankan dengan Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Akses Aplikasi**
   Setelah container berjalan, aplikasi dapat diakses di:
   - **API**: `http://localhost:8000`
   - **Swagger UI**: `http://localhost:8000/docs`
   - **Database**: `localhost:5432` (PostgreSQL)

---

## Dokumentasi API

Setelah server berjalan, akses dokumentasi interaktif di:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Perubahan Terbaru

1. Memperbaiki error "numpy.core.multiarray failed to import" dengan memperbarui versi numpy di requirements.txt
2. Memperbaiki error "module 'PIL.Image' has no attribute 'ANTIALIAS'" dengan menurunkan versi Pillow ke 9.x.x
3. Memperbaiki error "LokerCheck() got multiple values for keyword argument 'raw_ocr_text'" dengan menghapus key "raw_ocr_text" dari dictionary hasil parsing OCR