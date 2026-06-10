import uuid
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

# Magic bytes signatures for image validation (Security fix)
MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",  # JPEG signature
    b"\x89PNG\r\n\x1a\n": "png",  # PNG signature
}


def validate_magic_bytes(image_bytes: bytes) -> str | None:
    """Validate image based on magic bytes (file signature)."""
    for signature, img_type in MAGIC_BYTES.items():
        if image_bytes.startswith(signature):
            return img_type
    return None


def validate_image_and_get_extension(image_bytes: bytes) -> str:
    """Validasi uploaded bytes sebagai gambar valid dan return safe extension."""
    # First validate magic bytes
    magic_type = validate_magic_bytes(image_bytes)
    if magic_type is None:
        logger.warning("Profile image upload rejected: invalid magic bytes")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan format gambar yang valid.",
        )

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError) as e:
        logger.warning(f"Profile image upload rejected: PIL verification failed - {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan gambar valid atau file gambar rusak.",
        )

    extension = IMAGE_FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        logger.warning(f"Profile image upload rejected: unsupported format - {image_format}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    return extension


async def read_file_with_size_limit(file: UploadFile, max_size: int) -> bytes:
    """Read file in chunks and validate size BEFORE loading entire file into memory. (DoS prevention)"""
    chunks = []
    total_size = 0
    chunk_size = 512 * 1024  # 512KB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break

        total_size += len(chunk)

        if total_size > max_size:
            logger.warning(f"Profile image upload rejected: size {total_size} exceeds limit {max_size}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Ukuran file melebihi batas {MAX_FILE_SIZE_MB} MB.",
            )

        chunks.append(chunk)

    return b"".join(chunks)


def cleanup_old_image(image_filename: str) -> None:
    """Hapus file gambar lama jika ada."""
    if image_filename:
        old_path = PROFILE_UPLOAD_DIR / image_filename
        if old_path.exists():
            try:
                old_path.unlink()
                logger.info(f"Old profile image deleted: {image_filename}")
            except OSError as e:
                logger.error(f"Failed to delete old profile image: {e}")


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Lihat Profile User",
    tags=["profile"]
)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Mengambil data profile user yang sedang login."""
    logger.info(f"Profile accessed: user_id={current_user.id}")
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
    """Mengupdate data profile user (nama lengkap)."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Profile updated: user_id={current_user.id}")
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
    """Upload atau ganti gambar profile user dengan security improvements."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Profile image rejected: invalid content-type '{file.content_type}' from user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    # Read file with size validation BEFORE loading to memory
    try:
        image_bytes = await read_file_with_size_limit(file, MAX_FILE_SIZE_BYTES)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading profile image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membaca file upload.",
        )

    ext = validate_image_and_get_extension(image_bytes)

    new_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = PROFILE_UPLOAD_DIR / new_filename

    old_filename = current_user.profile_image
    if old_filename:
        cleanup_old_image(old_filename)

    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

    logger.info(f"Profile image uploaded: {new_filename} (user: {current_user.id}, size: {len(image_bytes)} bytes)")

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
    """Mengambil gambar profile user yang sedang login."""
    if not current_user.profile_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gambar profile tidak tersedia. Silakan upload gambar profile terlebih dahulu.",
        )

    image_path = PROFILE_UPLOAD_DIR / current_user.profile_image

    if not image_path.is_file():
        logger.error(f"Profile image file not found: {image_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File gambar profile tidak ditemukan di server.",
        )

    # Determine media type based on extension
    media_type = "image/jpeg" if image_path.suffix.lower() == ".jpg" else "image/png"

    logger.info(f"Profile image accessed: user_id={current_user.id}")
    return FileResponse(path=image_path, media_type=media_type)


@router.delete(
    "/profile",
    summary="Hapus Akun",
    tags=["profile"]
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Menghapus akun user beserta semua data terkait."""
    if current_user.profile_image:
        cleanup_old_image(current_user.profile_image)

    await db.delete(current_user)
    await db.commit()

    logger.info(f"Account deleted: user_id={current_user.id}")
    return {"message": "Akun berhasil dihapus. Semua data terkait telah dihapus."}