# Issue #9: Testing Infrastructure - Compatibility Issues

## Ringkasan

Setelah menjalankan tests, ditemukan beberapa masalah kompatibilitas yang perlu diperbaiki untuk menjalankan testing infrastructure dengan sukses.

---

## Masalah yang Ditemukan

### 1. ✅ FIXED: Missing `UserLogin` Schema

**File**: `app/schemas/user.py`

**Masalah**: Schema `UserLogin` tidak ada di `app/schemas/user.py`, padahal diperlukan oleh `app/api/v1/endpoints/auth.py`.

**Solusi**: Tambahkan schema `UserLogin` ke `app/schemas/user.py`:

```python
class UserLogin(BaseModel):
    email: EmailStr
    password: str
```

---

### 2. ✅ FIXED: Incorrect Import for `Token`

**File**: `app/api/v1/endpoints/auth.py`

**Masalah**: Auth endpoint mencoba import `Token` dari `app.schemas.user`, padahal `Token` ada di `app.schemas.token`.

**Solusi**: Update import statement:

```python
# Before
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse

# After
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.token import Token
```

---

### 3. ⚠️ NEEDS FIX: NumPy Version Incompatibility

**Error**:
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility. 
Expected 96 from C header, got 88 from PyObject
```

**File**: `app/services/ocr_service.py` (imports easyocr)

**Masalah**: 
- NumPy versi 2.2.6 terinstall
- EasyOCR, scikit-image, dan beberapa library lain membutuhkan NumPy versi lama
- Compatibility conflict dengan:
  - contourpy: requires numpy<2.0
  - mediapipe: requires numpy<2
  - tensorflow-intel: requires numpy<2.1.0
  - gensim: requires numpy<2.0
  - thinc: requires numpy<2.1.0

**Solusi yang Disarankan**:

#### Opsi 1: Downgrade NumPy (Tidak Disarankan)
```bash
pip install numpy==1.26.4
```
Tapi ini akan break tensorflow, mediapipe, dll.

#### Opsi 2: Mock OCR Service untuk Tests (Disarankan)
Modifikasi `app/services/ocr_service.py` untuk lazy-load EasyOCR, sehingga tidak di-import saat running tests tanpa OCR dependencies.

```python
# app/services/ocr_service.py
class OCRService:
    _reader = None
    
    @classmethod
    def get_reader(cls):
        if cls._reader is None:
            import easyocr
            cls._reader = easyocr.Reader(['en', 'id'], gpu=False)
        return cls._reader
```

#### Opsi 3: Skip OCR Tests dan Mock Service
Modifikasi `conftest.py` untuk mock `ocr_service` dan `scam_analysis_service`.

---

### 4. ⚠️ NEEDS FIX: Missing `UserResponse.username` Field

**File**: `app/schemas/user.py`

**Masalah**: `UserResponse` tidak memiliki field `username`, padahal `User` model memiliki field ini.

**Solusi**: Update `UserResponse`:

```python
class UserResponse(UserBase):
    id: int
    profile_image: Optional[str] = None
    username: Optional[str] = None  # Tambahkan ini
    
    model_config = {"from_attributes": True}
```

---

## Files yang Sudah Diperbaiki

1. ✅ `app/schemas/user.py` - Ditambahkan `UserLogin` schema dan `username` field
2. ✅ `app/api/v1/endpoints/auth.py` - Fix import `Token` dari module yang benar

---

## Files yang Perlu Diperbaiki

1. `app/services/ocr_service.py` - Implementasi lazy-load untuk EasyOCR
2. `tests/conftest.py` - Tambahkan mock untuk OCR service

---

## Testing Results

```
$ pytest tests/ -v --tb=short

FAILED tests/ - ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

Tests tidak bisa jalan karena NumPy version incompatibility dengan EasyOCR.

---

## Rekomendasi

1. **Untuk Development**: Downgrade NumPy dan test dengan mock OCR service
2. **Untuk CI/CD**: Gunakan mock service untuk menghindari dependency issues
3. **Untuk Production**: Pastikan NumPy version compatible dengan semua dependencies

---

## Acceptance Criteria

- [ ] Fix NumPy compatibility dengan EasyOCR (lazy-load atau mock)
- [ ] Semua unit tests bisa berjalan tanpa error
- [ ] Semua integration tests bisa berjalan tanpa error
- [ ] Coverage report bisa di-generate

---

## Notes

Masalah NumPy ini adalah environmental issue, bukan kode的问题. Disarankan untuk menggunakan Docker atau virtual environment yang terpisah untuk development dan testing.