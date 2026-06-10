# Issue #6: Share Loker Check Results to Community

## Ringkasan

Implementasi fitur untuk berbagi hasil pengecekan loker ke community. User dapat memilih hasil cek loker yang sudah di-submit untuk ditampilkan di community feed, sehingga orang lain bisa melihat dan mempelajari hasil deteksi scam tanpa perlu melakukan cek sendiri.

---

## Latar Belakang

Saat ini, hasil pengecekan loker hanya bisa dilihat oleh user yang melakukan pengecekan. Hal ini memiliki beberapa keterbatasan:

1. **Tidak ada sharing knowledge** — user yang menemukan loker mencurigakan tidak bisa berbagi temuan dengan komunitas.
2. **Tidak ada social proof** — orang lain tidak bisa melihat apakah suatu lowongan sudah pernah di-check dan hasilnya apa.
3. **Community awareness rendah** — user tidak bisa berkontribusi membangun database knowledge tentang loker mencurigakan.

Dengan fitur ini, user bisa berbagi hasil deteksi mereka ke community, sehingga:
- User lain bisa search/filter loker yang sudah di-check oleh komunitas
- Orang bisa melihat tren loker mencurigakan di suatu perusahaan/sumber
- Knowledge tentang scam patterns bisa dishare

---

## Scope Fitur

### Community Feed

| Komponen | Deskripsi |
|---|---|
| **Share to Community** | User mempublish hasil cek loker yang sudah di-submit ke community feed |
| **Unshare from Community** | User bisa menarik kembali hasil yang sudah dishare |
| **Community Feed** | List semua hasil yang dishare ke community (paginated, filterable) |
| **Community Detail** | Detail satu hasil yang dishare ke community |

### Privacy & Ownership

| Komponen | Deskripsi |
|---|---|
| **Private by Default** | Hasil cek loker tidak otomatis dishare ke community |
| **Owner Control** | Hanya owner yang bisa share/unshare hasil miliknya |
| **Anonymous Option** | Opsional: tampilkan nama user atau anonymous di community feed |

---

## Perubahan Backend yang Disarankan

### 1. Model Database

#### a. Model `LokerCheck` — Modifikasi Field

| Field | Tipe | Deskripsi |
|---|---|---|
| `is_shared` | `Boolean` | Flag apakah hasil dishare ke community |
| `shared_at` | `DateTime` | Timestamp saat dishare ke community |
| `share_anonymous` | `Boolean` | Flag apakah dishare sebagai anonymous |

#### b. Model Baru `CommunityReport` (Opsional — untuk metadata tambahan)

| Field | Tipe | Deskripsi |
|---|---|---|
| `id` | `Integer` | Primary key |
| `loker_check_id` | `Integer` | Foreign key ke `loker_checks` (unique, one-to-one) |
| `view_count` | `Integer` | Jumlah view (untuk analytics) |
| `like_count` | `Integer` | Jumlah like (untuk engagement) |
| `report_reason` | `String` | Alasan kenapa dishare (opsional) |

### 2. Migration

Buat migration baru untuk:
- Menambahkan kolom `is_shared` (Boolean, default `False`) ke tabel `loker_checks`
- Menambahkan kolom `shared_at` (DateTime, nullable) ke tabel `loker_checks`
- Menambahkan kolom `share_anonymous` (Boolean, default `False`) ke tabel `loker_checks`
- Opsional: Buat tabel `community_reports` untuk metadata tambahan

### 3. Schema Request/Response

#### a. Schema untuk Share/Unshare

```python
class ShareToCommunityRequest(BaseModel):
    anonymous: bool = False  # Apakah dishare sebagai anonymous

class ShareResponse(BaseModel):
    message: str
    is_shared: bool
    shared_at: datetime
```

#### b. Schema untuk Community Feed

```python
class CommunityReportResponse(BaseModel):
    id: int
    loker_check_id: int
    # Info loker (dari ocr_data atau individual fields)
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    scam_percentage: float
    scam_category: str
    scam_reason: Optional[str] = None
    # Info sharer (jika tidak anonymous)
    shared_by: Optional[str] = None  # full_name user
    shared_at: datetime
    # Metadata tambahan (jika ada)
    view_count: Optional[int] = None
    like_count: Optional[int] = None

    model_config = {"from_attributes": True}


class CommunityFeedResponse(BaseModel):
    total: int
    page: int
    size: int
    results: list[CommunityReportResponse]
```

### 4. Router / Endpoint API

#### Endpoint Baru:

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `POST` | `/api/v1/jobs/history/{check_id}/share` | Share hasil ke community | ✅ |
| `DELETE` | `/api/v1/jobs/history/{check_id}/share` | Unshare dari community | ✅ |
| `GET` | `/api/v1/community` | Community feed (paginated, filterable) | ❌ |
| `GET` | `/api/v1/community/{report_id}` | Detail satu report di community | ❌ |

#### Endpoint Modifikasi:

| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| `GET` | `/api/v1/jobs/history/{check_id}` | Tambahkan field `is_shared`, `shared_at` | ✅ |

### 5. Logic Business

#### a. Flow Share (`POST /history/{check_id}/share`)

```
1. Ambil loker_check berdasarkan check_id & user_id
2. Validasi check exists & milik user
3. Validasi bukan draft (harus sudah di-submit)
4. Validasi belum dishare (tidak bisa double share)
5. Update is_shared=True, shared_at=now(), share_anonymous
6. Opsional: Buat/Update CommunityReport metadata
7. Return ShareResponse
```

#### b. Flow Unshare (`DELETE /history/{check_id}/share`)

```
1. Ambil loker_check berdasarkan check_id & user_id
2. Validasi check exists & milik user
3. Validasi sudah dishare
4. Update is_shared=False, shared_at=None
5. Opsional: Hapus/update CommunityReport metadata
6. Return ShareResponse
```

#### c. Flow Community Feed (`GET /community`)

```
1. Query semua loker_check dengan is_shared=True
2. Apply filters (company, scam_category, date_range, search)
3. Paginate results
4. Return CommunityFeedResponse
```

### 6. Query Parameters untuk Community Feed

| Parameter | Tipe | Deskripsi |
|---|---|---|
| `page` | int | Nomor halaman (default 1) |
| `size` | int | Jumlah item per halaman (default 10, max 100) |
| `company` | string | Filter by company name (search) |
| `scam_category` | string | Filter by scam category |
| `min_scam` | float | Filter minimum scam percentage |
| `max_scam` | float | Filter maximum scam percentage |
| `search` | string | Search across job_title, company_name |

### 7. Error Handling

| Scenario | HTTP Status | Detail Message |
|---|---|---|
| Check tidak ditemukan | 404 | "Hasil pengecekan tidak ditemukan" |
| Check bukan milik user | 403 | "Anda tidak memiliki akses ke hasil ini" |
| Draft belum di-submit | 400 | "Hasil harus di-submit terlebih dahulu sebelum dishare" |
| Sudah dishare | 400 | "Hasil sudah dishare ke community" |
| Belum dishare (unshare) | 400 | "Hasil belum dishare ke community" |
| Report tidak ditemukan | 404 | "Report tidak ditemukan di community" |

---

## Acceptance Criteria

- [ ] User bisa share hasil cek loker yang sudah di-submit ke community
- [ ] User bisa unshare hasil dari community
- [ ] User bisa pilih anonymous atau tampilkan nama saat share
- [ ] Community feed menampilkan semua hasil yang dishare (paginated)
- [ ] Community feed bisa difilter (company, scam_category, date, search)
- [ ] Detail report di community bisa dilihat tanpa login
- [ ] User hanya bisa share/unshare hasil milik sendiri
- [ ] Hasil cek loker tidak otomatis dishare (private by default)
- [ ] Migration database berhasil dijalankan
- [ ] Unit test untuk semua endpoint baru
- [ ] Dokumentasi API (Swagger/Redoc) updated

---

## Catatan Tambahan

### UI/UX Consideration

Untuk frontend, alur yang disarankan:

```
1. User di halaman History Detail
   ↓
2. Tombol "Share to Community"
   - Modal: "Share anonymously?" (Ya/Tidak)
   ↓
3a. Jika Ya → Share sebagai anonymous
    - Tampilkan "Shared as Anonymous"
    - Badge "Shared to Community"
3b. Jika Tidak → Share dengan nama
    - Tampilkan "Shared by [Full Name]"
    - Badge "Shared to Community"
   ↓
4. Community Feed Page
   - List semua hasil yang dishare
   - Filter: company, scam level, date
   - Search: job title, company name
```

### Privacy Consideration

- Hasil cek loker **tidak otomatis** dishare
- User punya **kontrol penuh** untuk share/unshare
- **Anonymous option** tersedia untuk user yang tidak ingin tampilkan nama
- Data sensitif (email, phone) mungkin perlu di-mask di community feed

### Performance Consideration

- Add index pada `is_shared` untuk query optimization
- Consider caching untuk popular community feeds
- Add pagination yang efisien untuk large datasets

### Security Consideration

- Validasi ownership sebelum share/unshare
- User tidak bisa memodifikasi hasil orang lain
- Rate limiting untuk share/unshare actions
- Sanitize output di community feed (remove sensitive data)

### Future Enhancements (Out of Scope)

- Like/Upvote system untuk community reports
- Comment system untuk discussion
- Report/Flag system untuk inappropriate content
- Bookmark/Save system untuk users
- Analytics dashboard untuk trending scams