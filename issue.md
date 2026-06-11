# Issue: Missing Logout Endpoint

**Tanggal:** 2026-06-11  
**Endpoint:** `POST /api/v1/auth/logout` (belum ada)  
**Status:** Endpoint belum diimplementasi

---

## Deskripsi Masalah

Saat ini aplikasi **CekLoker** sudah memiliki:
- ✅ `POST /api/v1/auth/register` — Daftar akun baru
- ✅ `POST /api/v1/auth/login` — Login dan dapat JWT token
- ✅ `POST /api/v1/auth/token` — OAuth2 compatible login untuk Swagger UI
- ❌ `POST /api/v1/auth/logout` — **TIDAK ADA**

User yang sudah login tidak bisa melakukan logout dari sisi server. Token JWT tetap valid hingga expired (~24 jam default). Ini berarti:

1. Jika user logout dari aplikasi tapi seseorang拿到了 device mereka, token masih bisa digunakan selama belum expired
2. Tidak ada cara bagi user untuk **invalidate semua sesi** mereka
3. Tidak ada cara untuk **logout dari semua device** (jika user login di multiple devices)

---

## Analisis Arsitektur Auth Saat Ini

### Cara Kerja JWT di Aplikasi Ini

```
User Login → Server generate JWT token → Client simpan token
                ↓
        Token berisi: { "sub": "<user_id>", "exp": "<expiry>" }
                ↓
        Setiap request → Client kirim header "Authorization: Bearer <token>"
                ↓
        Server verify token signature dengan SECRET_KEY → allow/deny
```

### Kenapa Logout Tidak Langsung Invalid Token?

JWT bersifat **stateless** — server TIDAK menyimpan token setelah dibuat. Ini berarti:

```
┌─────────────────────────────────────────────────────────┐
│  Server tidak tahu token mana yang masih valid atau    │
│  sudah di-logout. Setiap token yang signature-nya      │
│  valid akan selalu diterima sampai expired.            │
└─────────────────────────────────────────────────────────┘
```

### Perbandingan: Session-Based vs JWT

| Aspek | Session-Based | JWT |
|-------|--------------|-----|
| Logout | Hapus session dari server | Tidak bisa (stateless) |
| Invalidate token | ✅ Bisa | ❌ Tidak langsung |
| Scalability | Perlu shared session store | ✅ Stateless |
| Logout semua sesi | ✅ Hapus semua sessions | ❌ Butuh token blocklist |

---

## Solusi: Token Blocklist (Server-Side Logout)

### Konsep

```
┌──────────────────────────────────────────────────┐
│                  SERVER                          │
│                                                   │
│  ┌─────────────┐    ┌───────────────────────┐   │
│  │  JWT Token  │───▶│  Verify Signature     │   │
│  │  dari user  │    └───────────┬───────────┘   │
│  └─────────────┘                │               │
│                    ┌─────────────▼───────────┐   │
│                    │  Cek apakah di          │   │
│                    │  Blocklist?            │   │
│                    └─────────────┬───────────┘   │
│                              │                    │
│           ┌──────────────────┴──────────────┐     │
│           ▼                                  ▼     │
│    ┌────────────┐                    ┌──────────┐ │
│    │    YES     │                    │    NO    │ │
│    │ Reject 401 │                    │ Allow ✓  │ │
│    └────────────┘                    └──────────┘ │
│                                                   │
│    ┌──────────────────────────────────────────┐   │
│    │         Token Blocklist (Redis/DB)        │   │
│    │  ┌────────────────────────────────────┐  │   │
│    │  │ jti | user_id | revoked_at | exp  │  │   │
│    │  │ abc123 | 5 | 2026-06-11 | 2026... │  │   │
│    │  └────────────────────────────────────┘  │   │
│    └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### Cara Kerja Logout dengan Blocklist

1. **Logout biasa:** Client kirim request ke `/logout` dengan token → Server tambahkan token ke blocklist dengan TTL = `exp - now`
2. **Logout semua sesi:** Server blocklist semua token yang pernah dibuat untuk user_id tersebut
3. **Verifikasi token:** Setiap request, cek apakah token ada di blocklist sebelum accept

---

## Checklist Implementasi

### Step 1: Buat Model TokenBlocklist

**File:** `app/models/token_blocklist.py` (atau `app/models/token.py`)

```python
# app/models/token_blocklist.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from app.core.database import Base

class TokenBlocklist(Base):
    __tablename__ = "token_blocklist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
```

> **Catatan:** `jti` (JWT ID) harus di-generate saat create token dan disimpan di token payload. Ini adalah unique identifier per token yang bisa di-blocklist.

### Step 2: Update security.py — Tambah jti ke Token

**File:** `app/core/security.py`

```python
import uuid

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    jti = str(uuid.uuid4())  # Unique ID per token
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "jti": jti,  # Tambahkan JTI untuk tracking
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### Step 3: Buat Service Token Blocklist

**File:** `app/services/token_blocklist_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from app.models.token_blocklist import TokenBlocklist

async def add_to_blocklist(
    db: AsyncSession,
    jti: str,
    user_id: int,
    expires_at: datetime
) -> None:
    """Add a token to the blocklist."""
    blocklist_entry = TokenBlocklist(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(blocklist_entry)
    await db.commit()

async def is_token_blocklisted(jti: str) -> bool:
    """Check if a token is in the blocklist."""
    result = await db.execute(
        select(TokenBlocklist).where(TokenBlocklist.jti == jti)
    )
    return result.scalar_one_or_none() is not None

async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> int:
    """Revoke all tokens for a user (logout from all devices)."""
    # Note: Untuk full implementation, perlu track semua JTI per user
    # atau pakai Redis untuk convenience
    pass

async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """Hapus entries yang sudah expired dari blocklist (cleanup)."""
    result = await db.execute(
        delete(TokenBlocklist).where(
            TokenBlocklist.expires_at < datetime.utcnow()
        )
    )
    await db.commit()
    return result.rowcount
```

### Step 4: Update deps.py — Cek Blocklist Saat Verifikasi Token

**File:** `app/api/deps.py`

```python
async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        
        # Cek apakah token sudah di-blocklist
        jti = payload.get("jti")
        if jti:
            is_blocklisted = await is_token_blocklisted(jti, db)
            if is_blocklisted:
                raise credentials_exception
        
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise credentials_exception
        user_id = int(token_data.sub)
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    # ... rest of the function
```

### Step 5: Tambah Endpoint Logout

**File:** `app/api/v1/endpoints/auth.py`

```python
@router.post(
    "/logout",
    summary="Logout dan Invalidasi Token",
    tags=["auth"],
    responses={
        200: {
            "description": "Logout berhasil",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout berhasil. Token sudah di-invalidasi."
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Token tidak valid"},
    },
)
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """
    Logout user dengan menambahkan token ke blocklist.
    
    - Token saat ini tidak bisa digunakan lagi setelah logout
    - User harus login ulang untuk mendapatkan token baru
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        
        if jti:
            await add_to_blocklist(db, jti, current_user.id, exp)
            logger.info(f"Token revoked for user: {current_user.email}, jti: {jti}")
        
        return {"message": "Logout berhasil. Token sudah di-invalidasi."}
    except JWTError as exc:
        logger.error(f"Logout failed: {exc}")
        raise InternalServerException("Gagal logout. Silakan coba lagi.")
```

### Step 6: Tambah Endpoint Logout All Devices (Opsional)

**File:** `app/api/v1/endpoints/auth.py`

```python
@router.post(
    "/logout-all",
    summary="Logout dari Semua Device",
    tags=["auth"],
)
async def logout_all_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout dari semua device yang login dengan akun ini.
    
    ⚠️ Implementasi ini membutuhkan tracking semua JTI per user.
    Jika pakai Redis, bisa menggunakan user_id sebagai key.
    """
    # Note: Implementasi penuh membutuhkan mekanisme untuk track
    # semua token yang dibuat untuk user_id tertentu
    pass
```

### Step 7: Buat Migration Alembic

```bash
alembic revision --autogenerate -m "Add token_blocklist table"
alembic upgrade head
```

### Step 8: Tambah Schema Response

**File:** `app/schemas/token.py` atau `app/schemas/auth.py`

```python
from pydantic import BaseModel

class LogoutResponse(BaseModel):
    message: str

class LogoutAllResponse(BaseModel):
    message: str
    revoked_count: int = 0
```

---

## Testing Checklist

### Test 1: Logout Berhasil (Token di-Blocklist)

```bash
# 1. Login untuk dapat token
curl -X POST "https://api.example.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 2. Logout dengan token tersebut
curl -X POST "https://api.example.com/api/v1/auth/logout" \
  -H "Authorization: Bearer eyJ..."

# Response: {"message": "Logout berhasil. Token sudah di-invalidasi."}
```

### Test 2: Token Setelah Logout Tidak Bisa Dipakai

```bash
# Gunakan token yang sama setelah logout
curl -X GET "https://api.example.com/api/v1/profile" \
  -H "Authorization: Bearer eyJ..."

# Expected Response:
# HTTP 401 Unauthorized
# {"detail": "Could not validate credentials"}
```

### Test 3: Token yang Tidak di-Logout Masih Valid

```bash
# Login dari device lain
curl -X POST "https://api.example.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Response: Token baru

# Token dari device lain masih bisa dipakai (karena tidak di-logout)
curl -X GET "https://api.example.com/api/v1/profile" \
  -H "Authorization: Bearer <token_baru>"

# Expected Response: HTTP 200 OK dengan data profile
```

### Test 4: Unit Tests

```python
# tests/unit/test_token_blocklist.py

import pytest
from datetime import datetime, timezone
from jose import jwt
from app.core.security import create_access_token, ALGORITHM
from app.core.config import settings

def test_token_has_jti():
    """Test bahwa setiap token punya unique JTI."""
    token1 = create_access_token(subject="1")
    token2 = create_access_token(subject="1")
    
    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[ALGORITHM])
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload1["jti"] is not None
    assert payload2["jti"] is not None
    assert payload1["jti"] != payload2["jti"]  # JTI harus unique

@pytest.mark.asyncio
async def test_blocklist_rejects_token():
    """Test bahwa token di blocklist ditolak."""
    from app.services.token_blocklist_service import (
        add_to_blocklist, is_token_blocklisted
    )
    
    token = create_access_token(subject="1")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    
    # Add to blocklist
    await add_to_blocklist(
        db=db_session,  # dari fixture
        jti=payload["jti"],
        user_id=1,
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    )
    
    # Check is blocked
    is_blocked = await is_token_blocklisted(payload["jti"])
    assert is_blocked is True
```

---

## Ringkasan Checklist

- [ ] **File:** `app/models/token_blocklist.py` — Buat model untuk menyimpan revoked tokens
- [ ] **File:** `app/core/security.py` — Update `create_access_token()` untuk generate JTI (JWT ID) unique per token
- [ ] **File:** `app/services/token_blocklist_service.py` — Buat service untuk add/check blocklist
- [ ] **File:** `app/api/deps.py` — Update `get_current_user()` untuk cek blocklist sebelum allow request
- [ ] **File:** `app/api/v1/endpoints/auth.py` — Tambah endpoint `POST /logout` dan opsional `POST /logout-all`
- [ ] **File:** `app/schemas/auth.py` — Tambah `LogoutResponse` schema
- [ ] **Migration:** `alembic revision --autogenerate -m "Add token_blocklist table"` → `alembic upgrade head`
- [ ] **Test:** Tambah unit tests untuk token blocklist
- [ ] **Test:** Manual test logout flow
- [ ] **Deploy:** Commit & push ke GitHub