"""Community API endpoints with comprehensive error handling."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.exceptions import NotFoundException
from app.models.loker_check import LokerCheck
from app.schemas.loker import (
    CommunityReportResponse,
    CommunityFeedResponse,
)
from app.api.v1.responses import responses_community

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()


def mask_sensitive_data(check: LokerCheck) -> dict:
    """Create a dict from LokerCheck with masked sensitive data for community display."""
    return {
        "id": check.id,
        "loker_check_id": check.id,
        "job_title": check.job_title,
        "company_name": check.company_name,
        "info_source": check.info_source,
        "job_type": check.job_type,
        "salary": check.salary,
        "description": check.description,
        "company_email": check.masked_email,
        "phone_number": check.masked_phone,
        "scam_percentage": check.scam_percentage or 0.0,
        "scam_category": check.scam_category or "Unknown",
        "scam_reason": check.scam_reason,
        "shared_by": None if check.share_anonymous else check.user.full_name,
        "shared_anonymous": check.share_anonymous,
        "shared_at": check.shared_at,
        "created_at": check.created_at,
    }


@router.get(
    "",
    response_model=CommunityFeedResponse,
    summary="Community Feed - Semua Hasil yang Dishare",
    tags=["community"],
    responses={
        **responses_community(),
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
    },
)
async def get_community_feed(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    company: str | None = Query(default=None, description="Filter by company name"),
    scam_category: str | None = Query(default=None, description="Filter by scam category"),
    min_scam: float | None = Query(default=None, ge=0, le=100, description="Minimum scam percentage"),
    max_scam: float | None = Query(default=None, ge=0, le=100, description="Maximum scam percentage"),
    search: str | None = Query(default=None, description="Search across job_title and company_name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Mengembalikan semua hasil yang dishare ke community (paginated, filterable).
    
    Endpoint ini publik - tidak memerlukan autentikasi.
    """
    offset = (page - 1) * size
    base_query = select(LokerCheck).where(LokerCheck.is_shared == True)
    
    filters = []
    
    if company:
        filters.append(LokerCheck.company_name.ilike(f"%{company}%"))
    
    if scam_category:
        filters.append(LokerCheck.scam_category == scam_category)
    
    if min_scam is not None:
        filters.append(LokerCheck.scam_percentage >= min_scam)
    
    if max_scam is not None:
        filters.append(LokerCheck.scam_percentage <= max_scam)
    
    if search:
        search_filter = or_(
            LokerCheck.job_title.ilike(f"%{search}%"),
            LokerCheck.company_name.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    # Count total
    count_query = select(func.count()).select_from(LokerCheck).where(
        LokerCheck.is_shared == True
    )
    for f in filters:
        count_query = count_query.where(f)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get paginated results
    query = (
        select(LokerCheck)
        .options(selectinload(LokerCheck.user))
        .where(LokerCheck.is_shared == True)
        .order_by(LokerCheck.shared_at.desc())
        .offset(offset)
        .limit(size)
    )
    
    for f in filters:
        query = query.where(f)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    transformed_results = [
        CommunityReportResponse(**mask_sensitive_data(report))
        for report in reports
    ]
    
    logger.info(f"Community feed accessed: page={page}, size={size}, total={total}")
    
    return CommunityFeedResponse(
        total=total,
        page=page,
        size=size,
        results=transformed_results,
    )


@router.get(
    "/{report_id}",
    response_model=CommunityReportResponse,
    summary="Detail Report di Community",
    tags=["community"],
    responses={
        **responses_community(),
    },
)
async def get_community_report_detail(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Mengembalikan detail satu report di community berdasarkan ID.
    
    Endpoint ini publik - tidak memerlukan autentikasi.
    Data sensitif (email, phone) di-mask untuk privacy.
    """
    result = await db.execute(
        select(LokerCheck)
        .options(selectinload(LokerCheck.user))
        .where(
            LokerCheck.id == report_id,
            LokerCheck.is_shared == True
        )
    )
    report = result.scalar_one_or_none()
    
    if report is None:
        logger.warning(f"Community report not found: report_id={report_id}")
        raise NotFoundException("Report", report_id)
    
    logger.info(f"Community report detail accessed: report_id={report_id}")
    
    return CommunityReportResponse(**mask_sensitive_data(report))