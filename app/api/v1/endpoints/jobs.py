import uuid
import asyncio
import aiofiles
import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.loker_check import LokerCheck
from app.models.user import User
from app.schemas.loker import HistoryListResponse, LokerCheckResponse, LokerCheckSummary
from app.services import ocr_service, scam_analysis_service

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Folder tempat gambar pamflet disimpan (relatif terhadap root project)
UPLOAD_DIR = Path("uploads/loker")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_image_and_get_extension(image_bytes: bytes) -> str:
    """Validate uploaded bytes as a real image and return a safe extension."""
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


@router.post(
    "/check",
    response_model=LokerCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cek Loker dari Gambar Pamflet",
)
async def check_loker(
    file: UploadFile = File(..., description="Gambar pamflet loker (PNG/JPG, maks 10 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload gambar pamflet loker untuk dianalisis.

    - Validasi tipe & ukuran file.
    - Simpan gambar ke folder `uploads/loker/`.
    - Melakukan OCR untuk mengekstrak informasi lowongan.
    - Menganalisis potensi scam dari data yang diekstrak.
    - Menyimpan dan mengembalikan hasil analisis.
    """
    # --- Validasi tipe file ---
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

    image_bytes = await file.read()

    # --- Validasi ukuran file ---
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran file melebihi batas {MAX_FILE_SIZE_MB} MB.",
        )

    ext = validate_image_and_get_extension(image_bytes)

    # --- Simpan gambar ke disk ---
    image_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / image_filename

    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

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
    except Exception as exc:
        await db.rollback()
        save_path.unlink(missing_ok=True)

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File gambar tidak ditemukan di server.",
        )

    return FileResponse(path=image_path)
