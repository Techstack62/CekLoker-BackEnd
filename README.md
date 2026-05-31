# CekLoker Backend API

Backend API untuk aplikasi **CekLoker**, sebuah platform yang bertujuan untuk mendeteksi lowongan pekerjaan (loker) palsu atau asli menggunakan model AI. 

Proyek ini dibangun menggunakan arsitektur modular yang rapi (Clean Architecture) dengan teknologi modern berbasis asinkron.

## Tech Stack
- **Web Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (Async dengan `asyncpg`)
- **Database Migrations**: Alembic
- **Validation & Configuration**: Pydantic v2 & Pydantic Settings
- **Authentication**: JWT (JSON Web Tokens) dengan `python-jose` & `passlib` (Bcrypt)

---

## Prasyarat (Prerequisites)
Pastikan sistem Anda sudah terinstal:
- Python 3.10 atau lebih baru.
- PostgreSQL Server.

---

## Cara Setup (Local Development)

### 1. Clone Repository & Setup Virtual Environment
```bash
# Clone repository
git clone https://github.com/Techstack62/CekLoker-BackEnd.git
cd CekLoker-BackEnd

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# (Alternatif untuk Linux/Mac)
# source venv/bin/activate
```

### 2. Install Dependensi
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables
1. Salin file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
2. Buka `.env` dan sesuaikan kredensial koneksi database PostgreSQL Anda pada variabel `DATABASE_URL`.
   Contoh format: `postgresql+asyncpg://<USER>:<PASSWORD>@localhost:5432/<DB_NAME>`

### 4. Setup Database & Migrasi
Pastikan PostgreSQL Anda sudah berjalan dan database kosong (contoh: `cek_loker`) sudah dibuat. Kemudian jalankan migrasi database agar tabel dibuat secara otomatis:
```bash
alembic upgrade head
```

### 5. Jalankan Aplikasi
```bash
uvicorn app.main:app --reload
```
Aplikasi akan berjalan di `http://localhost:8000`.

---

## Dokumentasi API (Swagger UI)
FastAPI secara otomatis menyediakan dokumentasi interaktif yang dapat diakses melalui browser Anda setelah server berjalan:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Fitur Tersedia Saat Ini
1. **Authentication:**
   - `POST /api/v1/auth/register`: Mendaftarkan user baru (menyimpan password dengan aman menggunakan Bcrypt).
   - `POST /api/v1/auth/login`: Autentikasi user dan memberikan JWT Token.

*Fitur deteksi Loker dengan Model AI akan diimplementasikan pada fase berikutnya.*
