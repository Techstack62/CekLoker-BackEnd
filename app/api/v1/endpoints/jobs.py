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
from app.schemas.loker import (
    OCRResultResponse,
    OCRData,
    OCRReviewRequest,
    LokerCheckResponse,
    LokerCheckSummary,
    HistoryListResponse,
    DraftListResponse,
)
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

# Upload directory for job images
UPLOAD_DIR = Path("uploads/loker")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Magic bytes signatures for image validation (High Priority security fix)
MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",  # JPEG signature
    b"\x89PNG\r\n\x1a\n": "png",  # PNG signature
}


def validate_magic_bytes(image_bytes: bytes) -> str | None:
    """
    Validate image based on magic bytes (file signature).
    Returns the image type if valid, None otherwise.
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
    magic_type = validate_magic_bytes(image_bytes)
    if magic_type is None:
        logger.warning("Upload rejected: invalid magic bytes (possible file spoofing attempt)")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File bukan format gambar yang valid.",
        )

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
    """
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break

        total_size += len(chunk)

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
    "/ocr",
    response_model=OCRResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Gambar → OCR → Preview Hasil untuk Review",
    tags=["jobs"],
    deprecated=False,
)
@limiter.limit("10/minute")
async def upload_for_ocr(
    request: Request,
    file: UploadFile = File(..., description="Gambar pamflet loker (PNG/JPG, maks 10 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stage 1: Upload gambar untuk OCR dan review hasil.
    
    - Validasi tipe & ukuran file (DoS prevention)
    - Validasi magic bytes (file spoofing prevention)
    - Simpan gambar ke folder uploads/loker/
    - Jalankan OCR untuk ekstrak teks
    - Simpan hasil sebagai draft (belum dianalisis)
    - Return hasil OCR untuk user review
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Upload rejected: invalid content-type '{file.content_type}' from user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file tidak didukung. Gunakan PNG atau JPG.",
        )

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

    ext = validate_image_and_get_extension(image_bytes)

    image_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / image_filename

    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

    logger.info(f"Image saved: {image_filename} (user: {current_user.id}, size: {len(image_bytes)} bytes)")

    try:
        raw_text = await asyncio.to_thread(ocr_service.extract_text_from_image, image_bytes)
        parsed = ocr_service.parse_ocr_text(raw_text)

        loker_check = LokerCheck(
            user_id=current_user.id,
            image_filename=image_filename,
            raw_ocr_text=raw_text,
            ocr_data=parsed,
            is_draft=True,
            **parsed,
        )
        db.add(loker_check)
        await db.commit()
        await db.refresh(loker_check)

        logger.info(f"OCR draft created: id={loker_check.id}, user={current_user.id}")

        return OCRResultResponse(
            id=loker_check.id,
            image_filename=loker_check.image_filename,
            raw_text=raw_text,
            ocr_data=OCRData(**parsed),
            is_draft=True,
            created_at=loker_check.created_at,
        )
    except Exception as exc:
        await db.rollback()
        save_path.unlink(missing_ok=True)
        logger.error(f"Error processing OCR: {exc}", exc_info=True)

        if isinstance(exc, HTTPException):
            raise exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gagal memproses gambar. Detail: {exc}",
        )


@router.get(
    "/drafts",
    response_model=DraftListResponse,
    summary="List Semua Draft User",
    tags=["jobs"],
)
async def get_drafts(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan semua draft (belum di-submit) milik user yang sedang login (paginated).
    """
    offset = (page - 1) * size

    count_result = await db.execute(
        select(func.count()).where(
            LokerCheck.user_id == current_user.id,
            LokerCheck.is_draft == True
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(LokerCheck)
        .where(
            LokerCheck.user_id == current_user.id,
            LokerCheck.is_draft == True
        )
        .order_by(LokerCheck.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    drafts = result.scalars().all()

    return DraftListResponse(
        total=total,
        page=page,
        size=size,
        results=[
            OCRResultResponse(
                id=d.id,
                image_filename=d.image_filename,
                raw_text=d.raw_ocr_text or "",
                ocr_data=OCRData(**d.ocr_data) if d.ocr_data else OCRData(),
                is_draft=d.is_draft,
                created_at=d.created_at,
            )
            for d in drafts
        ],
    )


@router.get(
    "/drafts/{draft_id}",
    response_model=OCRResultResponse,
    summary="Detail Satu Draft",
    tags=["jobs"],
)
async def get_draft_detail(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan detail lengkap satu draft berdasarkan ID.
    Hanya bisa diakses oleh pemilik draft tersebut.
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft tidak ditemukan.",
        )

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft access: user {current_user.id} tried to access draft_id {draft_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke draft ini.",
        )

    if not draft.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft sudah di-submit. Gunakan endpoint history.",
        )

    return OCRResultResponse(
        id=draft.id,
        image_filename=draft.image_filename,
        raw_text=draft.raw_ocr_text or "",
        ocr_data=OCRData(**draft.ocr_data) if draft.ocr_data else OCRData(),
        is_draft=draft.is_draft,
        created_at=draft.created_at,
    )


@router.put(
    "/drafts/{draft_id}",
    response_model=OCRResultResponse,
    summary="Update/Edit Hasil OCR Draft",
    tags=["jobs"],
)
async def update_draft(
    draft_id: int,
    review: OCRReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengupdate data OCR draft. User bisa mengoreksi hasil OCR yang salah.
    Draft yang sudah di-submit tidak bisa diedit.
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft tidak ditemukan.",
        )

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft update: user {current_user.id} tried to update draft_id {draft_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke draft ini.",
        )

    if not draft.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft sudah di-submit dan tidak bisa diedit.",
        )

    # Update ocr_data with user corrections
    ocr_dict = draft.ocr_data or {}
    update_data = review.ocr_data.model_dump(exclude_unset=True)
    ocr_dict.update(update_data)

    draft.ocr_data = ocr_dict

    # Also update individual fields for backwards compatibility
    if review.ocr_data.job_title is not None:
        draft.job_title = review.ocr_data.job_title
    if review.ocr_data.job_type is not None:
        draft.job_type = review.ocr_data.job_type
    if review.ocr_data.info_source is not None:
        draft.info_source = review.ocr_data.info_source
    if review.ocr_data.company_name is not None:
        draft.company_name = review.ocr_data.company_name
    if review.ocr_data.company_email is not None:
        draft.company_email = review.ocr_data.company_email
    if review.ocr_data.phone_number is not None:
        draft.phone_number = review.ocr_data.phone_number
    if review.ocr_data.salary is not None:
        draft.salary = review.ocr_data.salary
    if review.ocr_data.description is not None:
        draft.description = review.ocr_data.description

    # Reset analysis results - need to resubmit after edit
    draft.scam_percentage = None
    draft.scam_category = None
    draft.scam_reason = None

    await db.commit()
    await db.refresh(draft)

    logger.info(f"Draft updated: id={draft_id}, user={current_user.id}")

    return OCRResultResponse(
        id=draft.id,
        image_filename=draft.image_filename,
        raw_text=draft.raw_ocr_text or "",
        ocr_data=OCRData(**draft.ocr_data) if draft.ocr_data else OCRData(),
        is_draft=draft.is_draft,
        created_at=draft.created_at,
    )


@router.post(
    "/drafts/{draft_id}/submit",
    response_model=LokerCheckResponse,
    summary="Submit Draft untuk Analisis Scam",
    tags=["jobs"],
)
async def submit_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit draft untuk analisis scam.
    
    - Validasi draft exists & milik user
    - Validasi bukan sudah di-submit
    - Jalankan scam analysis
    - Update is_draft=False, submitted_at=now()
    - Return hasil lengkap
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft tidak ditemukan.",
        )

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft submit: user {current_user.id} tried to submit draft_id {draft_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke draft ini.",
        )

    if not draft.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft sudah di-submit sebelumnya.",
        )

    if not draft.ocr_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Data OCR tidak valid.",
        )

    # Run scam analysis
    try:
        analysis = await asyncio.to_thread(scam_analysis_service.analyze_scam, draft.ocr_data)

        draft.is_draft = False
        draft.submitted_at = func.now()
        draft.scam_percentage = analysis.scam_percentage
        draft.scam_category = analysis.scam_category
        draft.scam_reason = analysis.scam_reason

        await db.commit()
        await db.refresh(draft)

        logger.info(f"Draft submitted and analyzed: id={draft_id}, user={current_user.id}")

        return LokerCheckResponse.model_validate(draft)
    except Exception as exc:
        await db.rollback()
        logger.error(f"Error analyzing draft: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gagal menganalisis draft. Detail: {exc}",
        )


@router.delete(
    "/drafts/{draft_id}",
    summary="Hapus Draft",
    tags=["jobs"],
)
async def delete_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Menghapus draft yang tidak diperlukan.
    Draft yang sudah di-submit tidak bisa dihapus.
    """
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft tidak ditemukan.",
        )

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft delete: user {current_user.id} tried to delete draft_id {draft_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke draft ini.",
        )

    if not draft.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft sudah di-submit dan tidak bisa dihapus.",
        )

    # Delete image file
    if draft.image_filename:
        image_path = UPLOAD_DIR / draft.image_filename
        if image_path.exists():
            image_path.unlink()

    await db.delete(draft)
    await db.commit()

    logger.info(f"Draft deleted: id={draft_id}, user={current_user.id}")

    return {"message": "Draft berhasil dihapus."}


# Legacy endpoint - kept for backwards compatibility
@router.post(
    "/check",
    response_model=LokerCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Deprecated] Cek Loker dari Gambar Pamflet - Gunakan /ocr",
    tags=["jobs"],
    deprecated=True,
)
@limiter.limit("10/minute")
async def check_loker_legacy(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ DEPRECATED: Gunakan endpoint POST /api/v1/jobs/ocr untuk alur baru dengan review OCR.
    
    Upload gambar pamflet loker untuk dianalisis (satu tahap langsung).
    """
    # Reuse OCR endpoint logic but auto-submit
    ocr_response = await upload_for_ocr(request, file, db, current_user)

    # Auto-submit for backwards compatibility
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == ocr_response.id)
    )
    draft = result.scalar_one()

    analysis = await asyncio.to_thread(scam_analysis_service.analyze_scam, draft.ocr_data)

    draft.is_draft = False
    draft.submitted_at = func.now()
    draft.scam_percentage = analysis.scam_percentage
    draft.scam_category = analysis.scam_category
    draft.scam_reason = analysis.scam_reason

    await db.commit()
    await db.refresh(draft)

    logger.info(f"Legacy check completed: id={draft.id}, user={current_user.id}")

    return LokerCheckResponse.model_validate(draft)


@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="Riwayat Pengecekan Loker Saya (Yang Sudah Di-submit)",
    tags=["jobs"],
)
async def get_history(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengembalikan riwayat pengecekan loker yang sudah di-submit (paginated).
    Draft tidak termasuk dalam history.
    """
    offset = (page - 1) * size

    count_result = await db.execute(
        select(func.count()).where(
            LokerCheck.user_id == current_user.id,
            LokerCheck.is_draft == False
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(LokerCheck)
        .where(
            LokerCheck.user_id == current_user.id,
            LokerCheck.is_draft == False
        )
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
    tags=["jobs"],
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

    return LokerCheckResponse.model_validate(check)


@router.get(
    "/history/{check_id}/image",
    response_class=FileResponse,
    summary="Gambar Pamflet dari Riwayat Pengecekan",
    tags=["jobs"],
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