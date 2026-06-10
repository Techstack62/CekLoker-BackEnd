import uuid
import os
import asyncio
import aiofiles
import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.user import ProfileResponse, UserUpdate
from app.core.config import settings

router = APIRouter()

# Konfigurasi upload profile image
PROFILE_UPLOAD_DIR = Path("uploads/profile")
PROFILE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
}
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_image_and_get_extension(image_bytes: bytes) -> str:
    """Validasi uploaded bytes sebagai gambar valid dan return safe extension."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan gambar valid atau file gambar rusak.",
        )

    extension = IMAGE_FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    return extension


def cleanup_old_image(image_filename: str) -> None:
    """Hapus file gambar lama jika ada."""
    if image_filename:
        old_path = PROFILE_UPLOAD_DIR / image_filename
        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass  # Abaikan jika gagal hapus


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Lihat Profile User",
    tags=["profile"]
)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Mengambil data profile user yang sedang login.
    Hanya bisa diakses oleh user yang sudah terautentikasi.
    """
    return current_user


@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="Edit Profile User",
    tags=["profile"]
)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mengupdate data profile user (nama lengkap).
    Hanya bisa diakses oleh user yang sudah terautentikasi.
    """
    # Update hanya field yang provided
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post(
    "/profile/image",
    response_model=ProfileResponse,
    summary="Upload atau Ganti Gambar Profile",
    tags=["profile"]
)
async def upload_profile_image(
    file: UploadFile = File(..., description="Gambar profile (PNG/JPG, maks 5 MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload atau ganti gambar profile user.
    
    - Validasi tipe & ukuran file
    - Hapus gambar profile lama jika ada
    - Simpan gambar baru ke folder uploads/profile/
    - Update path gambar di database
    
    Hanya bisa diakses oleh user yang sudah terautentikasi.
    """
    # Validasi tipe file dari Content-Type header
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    # Baca file (dengan validasi ukuran)
    image_bytes = await file.read()
    
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran file melebihi batas {MAX_FILE_SIZE_MB} MB.",
        )

    # Validasi konten file adalah gambar valid
    ext = validate_image_and_get_extension(image_bytes)

    # Simpan gambar baru dengan UUID
    new_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = PROFILE_UPLOAD_DIR / new_filename

    # Hapus gambar lama sebelum menyimpan yang baru
    old_filename = current_user.profile_image
    if old_filename:
        cleanup_old_image(old_filename)

    # Tulis file baru
    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

    # Update path gambar di database
    current_user.profile_image = new_filename
    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.get(
    "/profile/image",
    summary="Lihat Gambar Profile",
    tags=["profile"]
)
async def get_profile_image(
    current_user: User = Depends(get_current_user),
):
    """
    Mengambil gambar profile user yang sedang login.
    
    Jika user belum mengupload gambar profile, akan mengembalikan 404.
    Hanya bisa diakses oleh user yang sudah terautentikasi.
    """
    if not current_user.profile_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gambar profile tidak tersedia. Silakan upload gambar profile terlebih dahulu.",
        )

    image_path = PROFILE_UPLOAD_DIR / current_user.profile_image
    
    if not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File gambar profile tidak ditemukan di server.",
        )

    return FileResponse(path=image_path)


@router.delete(
    "/profile",
    summary="Hapus Akun",
    tags=["profile"]
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Menghapus akun user beserta semua data terkait (riwayat pengecekan loker).
    
    - Hapus gambar profile jika ada
    - Hapus semua data user dari database (cascade delete)
    
    Tindakan ini **tidak dapat dibatalkan**.
    Hanya bisa diakses oleh user yang sudah terautentikasi.
    """
    # Hapus gambar profile jika ada
    if current_user.profile_image:
        cleanup_old_image(current_user.profile_image)

    # Hapus user dari database (cascade akan hapus loker_checks)
    await db.delete(current_user)
    await db.commit()

    return {"message": "Akun berhasil dihapus. Semua data terkait telah dihapus."}