# Issue #5: Two-Stage Job Check dengan Review OCR Result

## Ringkasan

Implementasi alur pengecekan loker dua tahap dengan fitur review hasil OCR sebelum dilakukan analisis scam. User dapat mengoreksi hasil ekstraksi teks sebelum submission ke model deteksi scam.

---

## Latar Belakang

Saat ini, proses cek loker berjalan dalam **satu tahap** langsung: upload gambar → OCR → analisis scam secara otomatis. Hal ini memiliki beberapa masalah:

1. **OCR tidak selalu sempurna** — hasil ekstraksi bisa salah, terutama untuk gambar dengan kualitas rendah atau font yang tidak umum.
2. **User tidak punya kontrol** — hasil OCR yang salah langsung masuk ke analisis, menghasilkan deteksi yang tidak akurat.
3. **Tidak ada机会 untuk koreksi** — user tidak bisa memperbaiki data sebelum analisis dilakukan.

Dengan alur baru ini, user mendapatkan **kontrol penuh** atas data yang akan dianalisis, sehingga hasil deteksi scam menjadi lebih akurat.

---

## Scope Fitur

### Stage 1: OCR & Review (Baru)

| Komponen | Deskripsi |
|---|---|
| **Upload Gambar** | User upload gambar pamflet loker (PNG/JPG, maks 10 MB) |
| **Ekstraksi OCR** | Sistem melakukan OCR untuk mengekstrak teks dari gambar |
| **Preview Hasil OCR** | Sistem mengembalikan hasil OCR dalam format terstruktur untuk direview oleh user |
| **Form Koreksi** | User dapat memperbaiki hasil OCR yang salah (nama loker, perusahaan, email, dll.) |
| **Simpan Draft** | Hasil OCR (beserta koreksi) disimpan sebagai draft sebelum analisis |

### Stage 2: Analisis & Submit (Modifikasi dari flow existing)

| Komponen | Deskripsi |
|---|---|
| **Submit untuk Analisis** | User submit data yang sudah dikoreksi untuk dilakukan analisis scam |
| **Scam Analysis** | Model menganalisis data dan mengembalikan hasil deteksi |
| **Simpan Hasil Akhir** | Hasil analisis disimpan ke riwayat user |

---

## Perubahan Backend yang Disarankan

### 1. Model Database

#### a. Model `LokerCheck` — Modifikasi Field

| Field | Tipe | Deskripsi |
|---|---|---|
| `ocr_data` | `JSON` | Hasil OCR dalam format JSON (dict) |
| `ocr_raw_text` | `Text` | Teks mentah hasil OCR |
| `is_draft` | `Boolean` | Flag apakah masih draft atau sudah submit |
| `submitted_at` | `DateTime` | Timestamp saat user submit untuk analisis |

> **Catatan:** Field-field existing (`job_title`, `company_name`, dll.) tetap ada tetapi akan di-override oleh `ocr_data` saat submission.

#### b. Model Baru `LokerDraft` (Opsional — jika ingin simpan multiple drafts)

| Field | Tipe | Deskripsi |
|---|---|---|
| `id` | `Integer` | Primary key |
| `user_id` | `Integer` | Foreign key ke `users` |
| `loker_check_id` | `Integer` | Foreign key ke `LokerCheck` (nullable, untuk draft tanpa submission) |
| `ocr_data` | `JSON` | Hasil OCR (sudah diedit oleh user) |
| `image_filename` | `String` | Path ke gambar |
| `created_at` | `DateTime` | Timestamp pembuatan draft |
| `updated_at` | `DateTime` | Timestamp update terakhir |

### 2. Migration

Buat migration baru untuk:
- Menambahkan kolom `ocr_data` (JSON) ke tabel `loker_checks`
- Menambahkan kolom `is_draft` (Boolean, default `True`) ke tabel `loker_checks`
- Menambahkan kolom `submitted_at` (DateTime, nullable) ke tabel `loker_checks`
- Rename/keep `raw_ocr_text` atau bisa dihapus jika `ocr_data` sudah mencakup semuanya

### 3. Schema Request/Response

#### a. Schema untuk OCR Result Preview

```python
class OCRData(BaseModel):
    job_title: Optional[str] = None
    job_type: Optional[str] = None
    info_source: Optional[str] = None
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    phone_number: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None

class OCRResultResponse(BaseModel):
    check_id: int
    image_filename: str
    raw_text: str  # Teks mentah OCR
    ocr_data: OCRData  # Hasil parsing terstruktur
    is_draft: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

#### b. Schema untuk OCR Review/Edit

```python
class OCRDataUpdate(BaseModel):
    job_title: Optional[str] = None
    job_type: Optional[str] = None
    info_source: Optional[str] = None
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    phone_number: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None

class OCRReviewRequest(BaseModel):
    ocr_data: OCRDataUpdate
```

### 4. Router / Endpoint API

#### Endpoint Baru:

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/api/v1/jobs/ocr` | Upload gambar → OCR → return hasil untuk review | ✅ |
| `GET` | `/api/v1/jobs/drafts` | List semua draft user (paginated) | ✅ |
| `GET` | `/api/v1/jobs/drafts/{draft_id}` | Detail satu draft | ✅ |
| `PUT` | `/api/v1/jobs/drafts/{draft_id}` | Update/edit hasil OCR draft | ✅ |
| `POST` | `/api/v1/jobs/drafts/{draft_id}/submit` | Submit draft untuk analisis scam | ✅ |
| `DELETE` | `/api/v1/jobs/drafts/{draft_id}` | Hapus draft | ✅ |

#### Endpoint Modifikasi:

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/api/v1/jobs/check` | **Deprecated** — Gunakan `/jobs/ocr` | ✅ |

> Endpoint lama `/check` bisa di-deprecate atau di-redirect ke flow baru.

### 5. Logic Business

#### a. Flow OCR (`POST /jobs/ocr`)

```
1. Validasi file upload (tipe, ukuran)
2. Simpan gambar ke uploads/loker/
3. Jalankan OCR → extract raw text
4. Parse raw text → extract structured data (ocr_data)
5. Buat LokerCheck baru dengan:
   - image_filename
   - raw_ocr_text
   - ocr_data (JSON)
   - is_draft = True
   - submitted_at = None
6. Return OCRResultResponse
```

#### b. Flow Submit (`POST /jobs/drafts/{draft_id}/submit`)

```
1. Ambil draft berdasarkan draft_id & user_id
2. Validasi draft exists & milik user
3. Validasi bukan sudah di-submit (is_draft = True)
4. Update is_draft = False, submitted_at = now()
5. Jalankan scam analysis dengan ocr_data
6. Update hasil analysis (scam_percentage, scam_category, scam_reason)
7. Return LokerCheckResponse (hasil lengkap)
```

#### c. Flow Edit Draft (`PUT /jobs/drafts/{draft_id}`)

```
1. Ambil draft berdasarkan draft_id & user_id
2. Validasi draft exists & milik user
3. Validasi bukan sudah di-submit
4. Update ocr_data dengan data baru dari request
5. Reset hasil analysis (jika ada) — perlu di-submit ulang setelah edit
6. Return OCRResultResponse (updated)
```

### 6. Upload Directory

Struktur folder `uploads/loker/` tetap sama (tidak perlu perubahan).

### 7. Error Handling

| Scenario | HTTP Status | Detail Message |
|---|---|---|
| Draft tidak ditemukan | 404 | "Draft tidak ditemukan" |
| Draft bukan milik user | 403 | "Anda tidak memiliki akses ke draft ini" |
| Draft sudah di-submit | 400 | "Draft sudah di-submit dan tidak bisa diedit" |
| Submit gagal (OCR data kosong) | 422 | "Data OCR tidak valid" |

---

## Acceptance Criteria

- [ ] User bisa upload gambar dan langsung mendapatkan hasil OCR untuk direview
- [ ] User bisa melihat list semua draft (belum di-submit)
- [ ] User bisa mengedit hasil OCR draft sebelum submit
- [ ] User bisa submit draft untuk analisis scam
- [ ] User bisa hapus draft yang tidak diperlukan
- [ ] Hasil analisis scam hanya di-generate setelah user submit
- [ ] Draft yang sudah di-submit tidak bisa diedit
- [ ] Endpoint lama `/check` tetap berfungsi atau di-deprecate dengan notice
- [ ] Migration database berhasil dijalankan
- [ ] Unit test untuk semua endpoint baru
- [ ] Dokumentasi API (Swagger/Redoc) updated

---

## Catatan Tambahan

### UI/UX Consideration

Untuk frontend, alur yang disarankan:

```
1. User upload gambar
   ↓
2. Tampilkan loading → "Memproses OCR..."
   ↓
3. Tampilkan hasil OCR dalam form
   - Semua field sudah pre-filled dari hasil OCR
   - User bisa edit field yang salah
   - Tombol "Simpan Draft" dan "Submit untuk Analisis"
   ↓
4a. Jika "Simpan Draft" → Simpan dan tampilkan "Draft disimpan"
4b. Jika "Submit untuk Analisis" → 
    - Loading "Menganalisis..."
    - Tampilkan hasil scam analysis
```

### Performance Consideration

- OCR adalah proses yang berat, jadi pastikan ada rate limiting
- Consider untuk menggunakan background task (Celery/Redis) untuk OCR jika volume tinggi

### Security Consideration

- Semua endpoint memerlukan JWT authentication
- User hanya bisa akses draft milik sendiri
- Validasi file upload tetap ketat (tipe, ukuran, content verification)
- Consider untuk add rate limiting per user untuk mencegah abuse

### Database Consideration

- `ocr_data` (JSON column) indexed untuk query yang sering (misal: search by company_name)
- Consider untuk add index pada `is_draft` dan `user_id`