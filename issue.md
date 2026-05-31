# Issue: Setup Initial Backend Architecture (FastAPI + PostgreSQL + SQLAlchemy + Alembic)

## Deskripsi
Membuat arsitektur dasar (boilerplate/scaffold) untuk backend API website **CekLoker**. Project ini menggunakan **FastAPI** sebagai web framework, **PostgreSQL** sebagai database utama, dan **SQLAlchemy 2.0 (Async)** sebagai ORM dengan **Alembic** untuk migrasi skema database. 

Arsitektur ini didesain menggunakan **Clean Architecture** (atau modular layered architecture) agar scalable, mudah dirawat, dan siap diintegrasikan dengan fitur deteksi loker palsu menggunakan model AI.

---

## Spesifikasi Tech Stack & Tools
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy 2.0+ (menggunakan `asyncpg` untuk koneksi asinkron)
- **Database Migrations:** Alembic
- **Settings & Config:** Pydantic Settings v2+
- **Dependency Management:** Poetry (direkomendasikan) atau `requirements.txt`
- **Linting & Formatting:** Ruff
- **Testing:** Pytest + HTTPX (untuk testing endpoint asinkron)
- **Containerization:** Docker + Docker Compose

---

## Struktur Folder Proyek (Recommended)
Model agent berikutnya harus mengikuti struktur direktori berikut:

```text
cek_loker_backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py         # Autentikasi user (register/login)
│   │   │   │   ├── job_check.py    # Fitur utama: cek loker asli/palsu
│   │   │   │   └── users.py        # Pengelolaan data user
│   │   │   └── api.py              # Router utama menggabungkan endpoint v1
│   │   └── deps.py                 # Dependency injection (e.g. get_db, get_current_user)
│   ├── core/
│   │   ├── config.py               # Konfigurasi aplikasi via Pydantic Settings
│   │   ├── database.py             # Setup SQLAlchemy async engine dan session maker
│   │   └── security.py             # Hashing password, JWT token handling
│   ├── models/
│   │   ├── base.py                 # Base declarative class untuk SQLAlchemy
│   │   ├── user.py                 # Model database User
│   │   └── job_vacancy.py          # Model database riwayat pengecekan Loker
│   ├── schemas/
│   │   ├── token.py                # Pydantic schemas untuk token JWT
│   │   ├── user.py                 # Pydantic schemas untuk User (input/output)
│   │   └── job_vacancy.py          # Pydantic schemas untuk input/output pengecekan loker
│   ├── services/
│   │   ├── ai_model.py             # Service untuk memanggil model AI (mock / placeholder)
│   │   └── job_checker.py          # Logika bisnis penanganan pengecekan loker
│   ├── main.py                     # Entrypoint aplikasi FastAPI
│   └── tests/
│       ├── conftest.py             # Setup testing database, client fixture
│       ├── test_auth.py
│       └── test_job_check.py
├── alembic/                        # Konfigurasi dan migrasi database Alembic
│   ├── env.py                      # Disesuaikan agar menggunakan async engine
│   ├── script.py.mako
│   └── versions/
├── .env.example                    # Template environment variables
├── .gitignore                      # Git ignore untuk Python & OS
├── alembic.ini                     # Konfigurasi Alembic
├── Dockerfile                      # Dockerfile multi-stage production-ready
├── docker-compose.yml              # Compose file untuk service web dan database
├── pyproject.toml                  # Konfigurasi Poetry dan linting Ruff
└── README.md                       # Petunjuk instruksi menjalankan proyek
```

---

## Langkah-Langkah Implementasi (Tasks)

### Task 1: Project Initialization & Dependency Setup
- Inisialisasi package manager (direkomendasikan menggunakan Poetry).
- Tambahkan library utama:
  `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `bcrypt`.
- Tambahkan library dev/testing:
  `pytest`, `pytest-asyncio`, `httpx`, `ruff`.
- Buat file konfigurasi `.gitignore` untuk menyaring file `.env`, `venv/`, `__pycache__/`, dll.
- Konfigurasikan **Ruff** di `pyproject.toml` untuk linting dan formatting otomatis.

### Task 2: Configuration & Environment Variables
- Buat model konfigurasi di `app/core/config.py` menggunakan `pydantic-settings`.
- Konfigurasi minimal yang dibutuhkan:
  - `PROJECT_NAME`
  - `API_V1_STR` (default: `/api/v1`)
  - `SECRET_KEY` (untuk JWT)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `DATABASE_URL` (PostgreSQL async URL, e.g., `postgresql+asyncpg://postgres:postgres@localhost:5432/cek_loker`)
  - `AI_MODEL_API_KEY` (jika ada integrasi API pihak ketiga seperti Gemini/Hugging Face)
- Sediakan file `.env.example` yang mencerminkan variabel di atas.

### Task 3: Database & ORM Setup (Async)
- Setup koneksi database asinkron menggunakan SQLAlchemy di `app/core/database.py`.
- Gunakan `create_async_engine` dan `async_sessionmaker`.
- Buat base model kelas deklaratif di `app/models/base.py` menggunakan `DeclarativeBase` baru dari SQLAlchemy 2.0.
- Implementasikan dependency injection `get_db` di `app/api/deps.py` untuk mengalirkan session database ke endpoint FastAPI.

### Task 4: Database Models & Migrations
- Buat model `User` di `app/models/user.py`:
  - `id` (UUID atau Integer PK)
  - `email` (Unique, Indexed)
  - `hashed_password`
  - `full_name`
  - `is_active` (boolean, default True)
  - `created_at` (timestamp)
- Buat model `JobVacancyCheck` di `app/models/job_vacancy.py`:
  - `id` (UUID atau Integer PK)
  - `title` (string)
  - `company` (string)
  - `description` (text)
  - `source_url` (string, optional)
  - `prediction` (string, e.g. "REAL" / "FAKE")
  - `confidence_score` (float)
  - `analysis_result` (text/JSON, detail hasil analisa model AI)
  - `checked_by` (Foreign Key ke `User`, optional/nullable jika bisa cek tanpa login)
  - `created_at` (timestamp)
- Inisialisasi Alembic (`alembic init -m async alembic` atau edit `alembic/env.py` agar kompatibel dengan async engine dan load target metadata dari `app/models/base.py`).
- Pastikan semua model di-import di file metadata agar terdeteksi oleh auto-generation migration Alembic.

### Task 5: Authentication & Security Services
- Di `app/core/security.py`, implementasikan fungsi `hash_password`, `verify_password`, dan `create_access_token`.
- Di `app/api/deps.py`, tambahkan dependency `get_current_user` untuk memvalidasi token JWT dan mengembalikan object user yang aktif.

### Task 6: Mock AI Service Layer
- Buat abstract class atau standard interface untuk pengecekan model AI di `app/services/ai_model.py`.
- Tulis mock implementation yang mensimulasikan hasil analisis kecerdasan buatan (mengeluarkan status "FAKE" atau "REAL" dengan skor keyakinan acak/berdasarkan heuristik sederhana). Ini agar backend siap diintegrasikan dengan model AI yang sesungguhnya di masa depan.

### Task 7: Schemas & Endpoints Setup
- Buat Pydantic schemas di direktori `app/schemas/` untuk:
  - User: `UserCreate`, `UserResponse`, `UserLogin`
  - JobVacancy: `JobCheckRequest` (input deskripsi/link loker), `JobCheckResponse` (output hasil analisis AI)
- Buat API router di `app/api/v1/endpoints/`:
  - `auth.py`: register user baru, login (mengeluarkan JWT token)
  - `job_check.py`: endpoint POST `/check` (menerima input loker, memanggil service AI mock, menyimpan ke DB, dan mengembalikan hasil analisis).
- Gabungkan router di `app/api/v1/api.py` dan sambungkan ke aplikasi utama di `app/main.py`.

### Task 8: Dockerization
- Buat `Dockerfile` multi-stage:
  - Stage 1: Build dependencies.
  - Stage 2: Runtime image yang ringan (misal menggunakan base image `python:3.11-slim`).
- Buat `docker-compose.yml` dengan dua service:
  1. `db`: Postgres database service dengan volume persistence dan basic healthcheck.
  2. `web`: Service FastAPI yang bergantung pada `db`, dengan environment variables yang terhubung ke database Postgres container.

### Task 9: Basic Testing Setup
- Konfigurasi `pytest` di `app/tests/conftest.py` dengan database testing SQLite in-memory atau database PostgreSQL terpisah untuk testing.
- Buat async client fixture menggunakan `httpx.AsyncClient`.
- Buat setidaknya satu test case sederhana untuk:
  - Registrasi & Login user.
  - Endpoint cek loker (menggunakan dependency override untuk mock database / AI service).

---

## Kriteria Penerimaan (Definition of Done)
1. Struktur folder sesuai dengan rancangan.
2. Aplikasi FastAPI dapat dijalankan secara lokal (via `uvicorn app.main:app --reload`) maupun lewat `docker-compose up --build`.
3. Endpoint Swagger docs dapat diakses secara normal di `/docs`.
4. Migrasi database pertama berhasil diinisiasi dan dieksekusi dengan Alembic (`alembic upgrade head`).
5. Kode lulus pengecekan Ruff linting (`ruff check .`) dan formatting (`ruff format --check .`).
6. Unit testing berjalan sukses (`pytest`).
