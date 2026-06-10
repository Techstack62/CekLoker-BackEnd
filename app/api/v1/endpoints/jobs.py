import uuid
import asyncio
import aiofiles
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Request, status
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.loker_check import LokerCheck
from app.models.user import User
from app.schemas.loker import HistoryListResponse, LokerCheckResponse, LokerCheckSummary
from app.services import ocr_service, scam_analysis_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiter for upload endpoint
limiter = Limiter(key_func=get_remote_address)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Magic bytes signatures for image validation (High Priority security fix)
MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",  # JPEG signature
    b"\x89PNG\r\n\x1a\n": "png",  # PNG signature
}


def validate_magic_bytes(image_bytes: bytes) -> str | None:
    """
    Validate image based on magic bytes (file signature).
    Returns the image type if valid, None otherwise.
    
    This is a HIGH PRIORITY security fix to prevent spoofed content-type attacks.
    """
    for signature, img_type in MAGIC_BYTES.items():
        if image_bytes.startswith(signature):
            return img_type
    return None


def validate_image_and_get_extension(image_bytes: bytes) -> str:
    """
    Validate uploaded bytes as a real image and return a safe extension.
    Performs both magic bytes validation and PIL verification.
    """
    # First, validate magic bytes (High Priority security fix)
    magic_type = validate_magic_bytes(image_bytes)
    if magic_type is None:
        logger.warning("Upload rejected: invalid magic bytes (possible file spoofing attempt)")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan format gambar yang valid.",
        )

    # Then validate with PIL to ensure it's a valid, readable image
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError) as e:
        logger.warning(f"Upload rejected: PIL verification failed - {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan gambar valid atau file gambar rusak.",
        )

    extension = IMAGE_FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        logger.warning(f"Upload rejected: unsupported image format - {image_format}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    return extension


async def read_file_with_size_limit(file: UploadFile, max_size: int) -> bytes:
    """
    Read file in chunks and validate size BEFORE loading entire file into memory.
    This is a HIGH PRIORITY security fix to prevent DoS attacks.
    
    Returns the file bytes if within size limit, raises HTTPException otherwise.
    """
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        
        total_size += len(chunk)
        
        # Check size limit BEFORE reading next chunk (DoS prevention)
        if total_size > max_size:
            logger.warning(
                f"Upload rejected: file size {total_size} bytes exceeds limit {max_size} bytes"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Ukuran file melebihi batas {MAX_FILE_SIZE_MB} MB.",
            )
        
        chunks.append(chunk)
    
    return b"".join(chunks)


@router.post(
    "/check",
    response_model=LokerCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cek Loker dari Gambar Pamflet",
)
@limiter.limit("10/minute")  # Rate limiting: 10 uploads per minute per IP
async def check_loker(
    request: Request,
    file: UploadFile = File(..., description="Gambar pamflet loker (PNG/JPG, maks 10 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload gambar pamflet loker untuk dianalisis.

    - Validasi tipe & ukuran file (size check BEFORE reading to memory - DoS prevention).
    - Validasi magic bytes (file signature validation).
    - Simpan gambar ke folder `uploads/loker/`.
    - Melakukan OCR untuk mengekstrak informasi lowongan.
    - Menganalisis potensi scam dari data yang diekstrak.
    - Menyimpan dan mengembalikan hasil analisis.
    
    Security improvements implemented:
    - File size validation BEFORE reading to memory (prevents DoS)
    - Magic bytes validation (prevents content-type spoofing)
    - Rate limiting (10 uploads per minute per IP)
    - Logging for security events
    """
    # --- Validasi tipe file (initial check, not final) ---
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(
            f"Upload rejected: invalid content-type '{file.content_type}' from user {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    # --- Read file with size validation BEFORE loading to memory (DoS prevention) ---
    try:
        image_bytes = await read_file_with_size_limit(file, MAX_FILE_SIZE_BYTES)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membaca file upload.",
        )

    # --- Validasi magic bytes (High Priority security fix) ---
    ext = validate_image_and_get_extension(image_bytes)

    # --- Simpan gambar ke disk ---
    image_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / image_filename

    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

    logger.info(f"Image saved: {image_filename} (user: {current_user.id}, size: {len(image_bytes)} bytes)")

    try:
        # --- OCR (dijalankan di thread pool agar tidak memblokir event loop) ---
        raw_text = await asyncio.to_thread(ocr_service.extract_text_from_image, image_bytes)

        parsed = ocr_service.parse_ocr_text(raw_text)

        # --- Scam Analysis (mock) ---
        analysis = await asyncio.to_thread(scam_analysis_service.analyze_scam, parsed)

        # --- Simpan hasil ke database ---
        loker_check = LokerCheck(
            user_id=current_user.id,
            image_filename=image_filename,   # hanya nama file, bukan full path
            **parsed,
            scam_percentage=analysis.scam_percentage,
            scam_category=analysis.scam_category,
            scam_reason=analysis.scam_reason,
        )
        db.add(loker_check)
        await db.commit()
        await db.refresh(loker_check)
        
        logger.info(f"Loker check completed: id={loker_check.id}, user={current_user.id}")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        # Clean up uploaded file on error
        save_path.unlink(missing_ok=True)
        logger.error(f"Error processing loker check: {exc}", exc_info=True)

        if isinstance(exc, HTTPException):
            raise exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gagal memproses gambar atau menyimpan hasil analisis. Detail: {exc}",
        )

    return loker_check


@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="Riwayat Pengecekan Loker Saya",
)
async def get_history(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan riwayat pengecekan loker milik user yang sedang login (paginated).
    """
    offset = (page - 1) * size

    count_result = await db.execute(
        select(func.count()).where(LokerCheck.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(LokerCheck)
        .where(LokerCheck.user_id == current_user.id)
        .order_by(LokerCheck.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    checks = result.scalars().all()

    return HistoryListResponse(
        total=total,
        page=page,
        size=size,
        results=[LokerCheckSummary.model_validate(c) for c in checks],
    )


@router.get(
    "/history/{check_id}",
    response_model=LokerCheckResponse,
    summary="Detail Riwayat Pengecekan Loker",
)
async def get_history_detail(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan detail lengkap satu hasil pengecekan berdasarkan ID.
    Hanya bisa diakses oleh pemilik riwayat tersebut.
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Riwayat pengecekan tidak ditemukan.",
        )

    if check.user_id != current_user.id:
        logger.warning(
            f"Unauthorized access attempt: user {current_user.id} tried to access check_id {check_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke riwayat ini.",
        )

    return check


@router.get(
    "/history/{check_id}/image",
    response_class=FileResponse,
    summary="Gambar Pamflet dari Riwayat Pengecekan",
)
async def get_history_image(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan file gambar pamflet untuk riwayat milik user yang sedang login.
    Endpoint ini menjaga agar user hanya bisa mengakses gambar miliknya sendiri.
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Riwayat pengecekan tidak ditemukan.",
        )

    if check.user_id != current_user.id:
        logger.warning(
            f"Unauthorized image access attempt: user {current_user.id} tried to access image for check_id {check_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke gambar ini.",
        )

    if not check.image_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gambar tidak tersedia.",
        )

    image_path = UPLOAD_DIR / check.image_filename
    if not image_path.is_file():
        logger.error(f"Image file not found: {image_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File gambar tidak ditemukan di server.",
        )

    return FileResponse(path=image_path)