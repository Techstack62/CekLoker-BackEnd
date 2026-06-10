# Docker Setup Guide

Panduan lengkap untuk menjalankan project CekLoker Backend menggunakan Docker secara lokal.

---

## Prerequisites

### 1. Install Docker Desktop

Pastikan Docker Desktop sudah terinstall di mesin kamu.

#### Windows

1. Download Docker Desktop dari [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Jalankan installer dan ikuti instruksi instalasi
3. **WSL 2 Backend**: Pastikan WSL 2 terinstall (direkomendasikan)
   ```powershell
   wsl --install
   ```
4. Restart komputer setelah instalasi selesai
5. Jalankan Docker Desktop dari Start Menu
6. Tunggu sampai icon Docker di system tray menunjukkan status "running" (warna hijau)

#### Mac

1. Download Docker Desktop dari [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Drag Docker.app ke folder Applications
3. Jalankan Docker Desktop dari Applications
4. Tunggu sampai icon Docker di menu bar menunjukkan status "running"

#### Linux (Ubuntu/Debian)

```bash
# Update apt
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg lsb-release

# Add Docker's GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group (agar tidak perlu sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Verifikasi Instalasi Docker

Setelah Docker terinstall, verifikasi dengan perintah berikut:

```bash
docker --version
docker compose version
```

Output yang diharapkan:
```
Docker version 24.x.x, build xxxxxxx
Docker Compose version v2.x.x
```

---

## Setup Project dengan Docker

### 1. Clone Repository (jika belum)

```bash
git clone https://github.com/Techstack62/CekLoker-BackEnd.git
cd CekLoker-BackEnd
```

### 2. Buat File Environment

Salin `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

File `.env` sudah dikonfigurasi dengan nilai default untuk Docker:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/cekloker
SECRET_KEY=change-this-secret-key-to-at-least-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DB_ECHO=false
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

> **Catatan**: Untuk environment production, pastikan `SECRET_KEY` diubah dengan nilai yang secure dan unik.

---

## Menjalankan Aplikasi

### Build dan Jalankan dengan Docker Compose

```bash
docker compose up --build
```

Perintah ini akan:
1. Build Docker image untuk aplikasi FastAPI
2. Membuat dan menjalankan container PostgreSQL
3. Menjalankan container aplikasi FastAPI
4. Menjalankan database migrations otomatis (via Alembic)

### Jalankan di Background (Detached Mode)

```bash
docker compose up --build -d
```

### Lihat Log

```bash
# Semua service
docker compose logs -f

# Service tertentu
docker compose logs -f app
docker compose logs -f db
```

---

## Service yang Berjalan

Setelah aplikasi berhasil dijalankan, service berikut akan tersedia:

| Service | URL | Deskripsi |
|---------|-----|-----------|
| **FastAPI App** | http://localhost:8000 | Backend API |
| **Swagger UI** | http://localhost:8000/docs | Dokumentasi API interaktif |
| **ReDoc** | http://localhost:8000/redoc | Dokumentasi API alternatif |
| **PostgreSQL** | localhost:5432 | Database (port eksternal) |

---

## Perintah Docker Compose yang Berguna

### Start Services
```bash
docker compose start
```

### Stop Services
```bash
docker compose stop
```

### Restart Services
```bash
docker compose restart
```

### Hapus Containers dan Volumes
```bash
docker compose down -v
```

> **Peringatan**: Perintah `-v` akan menghapus semua data di database. Gunakan dengan hati-hati!

### Rebuild Tanpa Cache
```bash
docker compose build --no-cache
```

### Eksekusi Perintah di Container

```bash
# Masuk ke shell container app
docker compose exec app bash

# Jalankan Alembic migrations
docker compose exec app alembic upgrade head

# Jalankan pytest
docker compose exec app pytest

# Jalankan Python shell
docker compose exec app python
```

### Lihat Status Container
```bash
docker compose ps
```

Output:
```
NAME          IMAGE               COMMAND                  SERVICE   CREATED   STATUS   PORTS
cekloker_db   postgres:15-alpine  "docker-entrypoint.s…"   db        ...       Up       0.0.0.0:5432->5432/tcp
cekloker_app  cekloker-backend    "uvicorn app.main:ap…"   app       ...       Up       0.0.0.0:8000->8000/tcp
```

---

## Troubleshooting

### Container Gagal Start

1. **Cek log error**:
   ```bash
   docker compose logs app
   ```

2. **Cek port冲突**:
   ```bash
   netstat -an | grep 8000
   netstat -an | grep 5432
   ```
   
   Jika port sudah digunakan, ubah port di `docker-compose.yml`.

3. **Cek Docker Desktop berjalan**:
   Pastikan Docker Desktop/icon Docker di system tray menunjukkan status running.

### Database Connection Error

1. **Tunggu database healthy**:
   ```bash
   docker compose ps
   ```
   
   Pastikan database status adalah `healthy` sebelum app fully running.

2. **Regenerate database**:
   ```bash
   docker compose down -v
   docker compose up --build
   ```

### EasyOCR Gagal (Out of Memory)

EasyOCR membutuhkan resource yang cukup. Untuk environment dengan memory terbatas:

1. Edit `docker-compose.yml`, tambahkan memory limit:
   ```yaml
   app:
     mem_limit: 4g
     build: ...
   ```

2. Atau pre-download model EasyOCR untuk menghindari download saat runtime:
   
   Uncomment baris ini di `Dockerfile`:
   ```dockerfile
   RUN python -c "import easyocr; easyocr.Reader(['en', 'id'], gpu=False, download=True)"
   ```

### Build Gagal (Python Dependencies)

1. **Hapus cache dan rebuild**:
   ```bash
   docker compose build --no-cache
   ```

2. **Cek requirements.txt**:
   Pastikan semua dependencies kompatibel dengan Python 3.10.

### Permission Issue (Linux)

Jika terjadi permission issue dengan folder uploads:

```bash
sudo chmod -R 777 uploads/
```

---

## Struktur Docker Files

```
CekLoker-BackEnd/
├── Dockerfile              # Build configuration untuk app
├── docker-compose.yml      # Orchestrasi container
├── .dockerignore          # Exclude files dari build context
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (local)
└── DOCKER.md              # Dokumentasi ini
```

---

## Development Workflow dengan Docker

### Hot Reload (Development)

Docker setup ini menggunakan volume mounting untuk code changes, tetapi untuk full hot reload:

```bash
# Jalankan dengan host network
docker compose up --build -d
```

Untuk development aktif, disarankan menjalankan secara langsung (non-Docker) seperti yang dijelaskan di README.md, dan gunakan Docker hanya untuk production atau CI/CD.

### Running Tests

```bash
# Jalankan semua test
docker compose exec app pytest

# Jalankan dengan coverage
docker compose exec app pytest --cov=app --cov-report=html

# Jalankan test tertentu
docker compose exec app pytest tests/unit/
```

---

## Cleanup

### Hapus Semua Docker Resources

```bash
# Stop dan hapus containers, networks
docker compose down

# Hapus containers, networks, DAN volumes (database)
docker compose down -v

# Hapus unused images
docker image prune -a

# Hapus semua stopped containers, unused networks, dangling images
docker system prune -a
```

### Reset Penuh

```bash
docker compose down -v --rmi all
docker system prune -a
docker compose up --build
```

---

## Catatan Penting

1. **Data Persistence**: Data PostgreSQL disimpan di Docker volume `postgres_data`. Data ini akan persist meskipun container dihentikan.

2. **Upload Files**: Folder `uploads/` di-mount sebagai volume. File yang diupload akan tersedia di host dan container.

3. **Secret Key**: Untuk production, selalu gunakan `SECRET_KEY` yang secure dan jangan pernah commit file `.env` ke GitHub.

4. **Port Forwarding**: Port 8000 (app) dan 5432 (PostgreSQL) harus available di host machine.

5. **Resource Limits**: Sesuaikan resource limit (CPU, memory) di Docker Desktop Settings sesuai kebutuhan.

---

## Referensi Tambahan

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)