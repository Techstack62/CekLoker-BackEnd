"""Job check endpoints with comprehensive error handling."""
import uuid
import asyncio
import aiofiles
import io
import logging
from pathlib import Path
from datetime import datetime

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
    ShareToCommunityRequest,
    ShareResponse,
)
from app.services import ocr_service, scam_analysis_service
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    UnauthorizedException,
    FileTooLargeException,
    UnsupportedMediaTypeException,
    FileCorruptedException,
    ConflictException,
    DraftNotSubmittedException,
    AlreadySharedException,
    NotSharedException,
    DraftAlreadySubmittedException,
    InternalServerException,
)
from app.api.v1.responses import (
    responses_file_upload,
    responses_401_403_404_500,
    responses_share,
)

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

UPLOAD_DIR = Path("uploads/loker")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
}


def validate_magic_bytes(image_bytes: bytes) -> str | None:
    """Validate image based on magic bytes."""
    for signature, img_type in MAGIC_BYTES.items():
        if image_bytes.startswith(signature):
            return img_type
    return None


def validate_image_and_get_extension(image_bytes: bytes) -> str:
    """Validate uploaded bytes as a real image and return safe extension."""
    magic_type = validate_magic_bytes(image_bytes)
    if magic_type is None:
        logger.warning("Upload rejected: invalid magic bytes")
        raise UnsupportedMediaTypeException("image/jpeg or image/png")

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            image_format = image.format
    except (UnidentifiedImageError, OSError) as e:
        logger.warning(f"Upload rejected: PIL verification failed - {e}")
        raise FileCorruptedException()

    extension = IMAGE_FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        raise UnsupportedMediaTypeException("image/jpeg or image/png")

    return extension


async def read_file_with_size_limit(file: UploadFile, max_size: int) -> bytes:
    """Read file in chunks and validate size."""
    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise FileTooLargeException(MAX_FILE_SIZE_MB)
        chunks.append(chunk)

    return b"".join(chunks)


# ========== Standard HTTP Error Response Definitions ==========
_AUTH_RESPONSES = {
    **responses_file_upload(),
    422: {
        "description": "Unprocessable Entity - Validation error (Pydantic validation failed)",
        "content": {
            "application/json": {
                "example": {
                    "error": "VALIDATION_ERROR",
                    "message": "Validasi data gagal.",
                    "details": {"field_errors": [{"field": "file", "message": "field required"}]},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_DRAFT_LIST_RESPONSES = {
    **responses_401_403_404_500(),
    422: {
        "description": "Unprocessable Entity - Validation error",
        "content": {
            "application/json": {
                "example": {
                    "error": "VALIDATION_ERROR",
                    "message": "Validasi data gagal.",
                    "details": {"field_errors": [{"field": "page", "message": "field required"}]},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_DRAFT_DETAIL_RESPONSES = {
    **responses_401_403_404_500(),
    400: {
        "description": "Bad Request - Draft already submitted",
        "content": {
            "application/json": {
                "example": {
                    "error": "BAD_REQUEST",
                    "message": "Draft sudah di-submit. Gunakan endpoint history.",
                    "details": {"field": None},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_DRAFT_UPDATE_RESPONSES = {
    **responses_401_403_404_500(),
    409: {
        "description": "Conflict - Draft already submitted",
        "content": {
            "application/json": {
                "example": {
                    "error": "DRAFT_ALREADY_SUBMITTED",
                    "message": "Draft sudah di-submit dan tidak bisa diedit.",
                    "details": None,
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_DRAFT_DELETE_RESPONSES = {
    **responses_401_403_404_500(),
    409: {
        "description": "Conflict - Draft already submitted",
        "content": {
            "application/json": {
                "example": {
                    "error": "DRAFT_ALREADY_SUBMITTED",
                    "message": "Draft sudah di-submit dan tidak bisa dihapus.",
                    "details": None,
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_SHARE_RESPONSES = {
    **responses_share(),
    422: {
        "description": "Unprocessable Entity - Validation error",
        "content": {
            "application/json": {
                "example": {
                    "error": "VALIDATION_ERROR",
                    "message": "Validasi data gagal.",
                    "details": {"field_errors": []},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    },
}

_HISTORY_RESPONSES = {
    **responses_401_403_404_500(),
}


@router.post(
    "/ocr",
    response_model=OCRResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Gambar → OCR → Preview Hasil untuk Review",
    tags=["jobs"],
    responses=_AUTH_RESPONSES,
)
@limiter.limit("10/minute")
async def upload_for_ocr(
    request: Request,
    file: UploadFile = File(..., description="Gambar pamflet loker (PNG/JPG, maks 10 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stage 1: Upload gambar untuk OCR dan review hasil."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaTypeException(file.content_type or "unknown")

    try:
        image_bytes = await read_file_with_size_limit(file, MAX_FILE_SIZE_BYTES)
    except HTTPException:
        raise

    ext = validate_image_and_get_extension(image_bytes)

    image_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / image_filename

    async with aiofiles.open(save_path, "wb") as out_file:
        await out_file.write(image_bytes)

    logger.info(f"Image saved: {image_filename} (user: {current_user.id})")

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
    except HTTPException:
        await db.rollback()
        save_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        await db.rollback()
        save_path.unlink(missing_ok=True)
        logger.error(f"Error processing OCR: {exc}", exc_info=True)
        raise BadRequestException(message=f"Gagal memproses gambar. Detail: {exc}")


@router.get(
    "/drafts",
    response_model=DraftListResponse,
    summary="List Semua Draft User",
    tags=["jobs"],
    responses=_DRAFT_LIST_RESPONSES,
)
async def get_drafts(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengembalikan semua draft (belum di-submit) milik user (paginated)."""
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
    responses=_DRAFT_DETAIL_RESPONSES,
)
async def get_draft_detail(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengembalikan detail lengkap satu draft berdasarkan ID."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise NotFoundException("Draft", draft_id)

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft access: user {current_user.id} tried to access draft_id {draft_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke draft ini.")

    if not draft.is_draft:
        raise BadRequestException("Draft sudah di-submit. Gunakan endpoint history.")

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
    responses={
        **_DRAFT_UPDATE_RESPONSES,
        422: {
            "description": "Unprocessable Entity - Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Validasi data gagal.",
                        "details": {"field_errors": [{"field": "ocr_data.job_title", "message": "field required"}]},
                        "timestamp": "2026-06-10T12:00:00Z"
                    }
                }
            }
        },
    },
)
async def update_draft(
    draft_id: int,
    review: OCRReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengupdate data OCR draft."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise NotFoundException("Draft", draft_id)

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft update: user {current_user.id} tried to update draft_id {draft_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke draft ini.")

    if not draft.is_draft:
        raise DraftAlreadySubmittedException("diedit")

    ocr_dict = draft.ocr_data or {}
    update_data = review.ocr_data.model_dump(exclude_unset=True)
    ocr_dict.update(update_data)
    draft.ocr_data = ocr_dict

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
    responses=_HISTORY_RESPONSES,
)
async def submit_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit draft untuk analisis scam."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise NotFoundException("Draft", draft_id)

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft submit: user {current_user.id} tried to submit draft_id {draft_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke draft ini.")

    if not draft.is_draft:
        raise BadRequestException("Draft sudah di-submit sebelumnya.")

    if not draft.ocr_data:
        raise BadRequestException("Data OCR tidak valid.")

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
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(f"Error analyzing draft: {exc}", exc_info=True)
        raise BadRequestException(message=f"Gagal menganalisis draft. Detail: {exc}")


@router.delete(
    "/drafts/{draft_id}",
    summary="Hapus Draft",
    tags=["jobs"],
    responses=_DRAFT_DELETE_RESPONSES,
)
async def delete_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Menghapus draft yang tidak diperlukan."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if draft is None:
        raise NotFoundException("Draft", draft_id)

    if draft.user_id != current_user.id:
        logger.warning(f"Unauthorized draft delete: user {current_user.id} tried to delete draft_id {draft_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke draft ini.")

    if not draft.is_draft:
        raise DraftAlreadySubmittedException("dihapus")

    if draft.image_filename:
        image_path = UPLOAD_DIR / draft.image_filename
        if image_path.exists():
            image_path.unlink()

    await db.delete(draft)
    await db.commit()

    logger.info(f"Draft deleted: id={draft_id}, user={current_user.id}")

    return {"message": "Draft berhasil dihapus."}


@router.post(
    "/check",
    response_model=LokerCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Deprecated] Cek Loker dari Gambar Pamflet - Gunakan /ocr",
    tags=["jobs"],
    deprecated=True,
    responses=_AUTH_RESPONSES,
)
@limiter.limit("10/minute")
async def check_loker_legacy(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """⚠️ DEPRECATED: Gunakan endpoint POST /api/v1/jobs/ocr untuk alur baru dengan review OCR."""
    ocr_response = await upload_for_ocr(request, file, db, current_user)

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
    responses=_DRAFT_LIST_RESPONSES,
)
async def get_history(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengembalikan riwayat pengecekan loker yang sudah di-submit (paginated)."""
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
    responses=_HISTORY_RESPONSES,
)
async def get_history_detail(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengembalikan detail lengkap satu hasil pengecekan berdasarkan ID."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise NotFoundException("Riwayat pengecekan", check_id)

    if check.user_id != current_user.id:
        logger.warning(f"Unauthorized access: user {current_user.id} tried to access check_id {check_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke riwayat ini.")

    return LokerCheckResponse.model_validate(check)


@router.get(
    "/history/{check_id}/image",
    response_class=FileResponse,
    summary="Gambar Pamflet dari Riwayat Pengecekan",
    tags=["jobs"],
    responses=_HISTORY_RESPONSES,
)
async def get_history_image(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mengembalikan file gambar pamflet untuk riwayat milik user."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise NotFoundException("Riwayat pengecekan", check_id)

    if check.user_id != current_user.id:
        logger.warning(f"Unauthorized image access: user {current_user.id} tried to access image for check_id {check_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke gambar ini.")

    if not check.image_filename:
        raise NotFoundException("Gambar", "tidak tersedia")

    image_path = UPLOAD_DIR / check.image_filename
    if not image_path.is_file():
        logger.error(f"Image file not found: {image_path}")
        raise NotFoundException("File gambar", "tidak ditemukan di server")

    return FileResponse(path=image_path)


# ============ Community Sharing Endpoints ============

@router.post(
    "/history/{check_id}/share",
    response_model=ShareResponse,
    summary="Share Hasil ke Community",
    tags=["jobs"],
    responses=_SHARE_RESPONSES,
)
async def share_to_community(
    check_id: int,
    share_request: ShareToCommunityRequest = ShareToCommunityRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Share hasil pengecekan loker ke community."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise NotFoundException("Hasil pengecekan", check_id)

    if check.user_id != current_user.id:
        logger.warning(f"Unauthorized share: user {current_user.id} tried to share check_id {check_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke hasil ini.")

    if check.is_draft:
        raise DraftNotSubmittedException()

    if check.is_shared:
        raise AlreadySharedException()

    check.is_shared = True
    check.shared_at = datetime.utcnow()
    check.share_anonymous = share_request.anonymous

    await db.commit()
    await db.refresh(check)

    logger.info(f"Check shared: id={check_id}, user={current_user.id}, anonymous={share_request.anonymous}")

    return ShareResponse(
        message="Berhasil dishare ke community." if not share_request.anonymous else "Berhasil dishare ke community secara anonymous.",
        is_shared=True,
        shared_at=check.shared_at,
    )


@router.delete(
    "/history/{check_id}/share",
    response_model=ShareResponse,
    summary="Unshare dari Community",
    tags=["jobs"],
    responses={
        **responses_share(),
        400: {
            "description": "Bad Request - Not shared",
            "content": {
                "application/json": {
                    "example": {
                        "error": "NOT_SHARED",
                        "message": "Hasil belum dishare ke community.",
                        "details": None,
                        "timestamp": "2026-06-10T12:00:00Z"
                    }
                }
            }
        },
    },
)
async def unshare_from_community(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tarik kembali hasil pengecekan dari community."""
    result = await db.execute(
        select(LokerCheck).where(LokerCheck.id == check_id)
    )
    check = result.scalar_one_or_none()

    if check is None:
        raise NotFoundException("Hasil pengecekan", check_id)

    if check.user_id != current_user.id:
        logger.warning(f"Unauthorized unshare: user {current_user.id} tried to unshare check_id {check_id}")
        raise ForbiddenException("Anda tidak memiliki akses ke hasil ini.")

    if not check.is_shared:
        raise NotSharedException()

    check.is_shared = False
    check.shared_at = None
    check.share_anonymous = False

    await db.commit()

    logger.info(f"Check unshared: id={check_id}, user={current_user.id}")

    return ShareResponse(
        message="Berhasil dihapus dari community.",
        is_shared=False,
        shared_at=None,
    )