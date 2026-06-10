"""
Community API endpoints for sharing loker check results.

This module provides public endpoints for viewing shared loker check results
and authenticated endpoints for sharing/unsharing user's own results.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.loker_check import LokerCheck
from app.models.user import User
from app.schemas.loker import (
    ShareToCommunityRequest,
    ShareResponse,
    CommunityReportResponse,
    CommunityFeedResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()


def mask_sensitive_data(check: LokerCheck) -> dict:
    """
    Create a dict from LokerCheck with masked sensitive data for community display.
    
    Security: Masks email and phone number to protect privacy while still
    providing useful information to the community.
    """
    return {
        "id": check.id,
        "loker_check_id": check.id,
        "job_title": check.job_title,
        "company_name": check.company_name,
        "info_source": check.info_source,
        "job_type": check.job_type,
        "salary": check.salary,
        "description": check.description,
        # Masked sensitive data
        "company_email": check.masked_email,
        "phone_number": check.masked_phone,
        # Analysis results
        "scam_percentage": check.scam_percentage or 0.0,
        "scam_category": check.scam_category or "Unknown",
        "scam_reason": check.scam_reason,
        # Sharer info (respects anonymous setting)
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
)
async def get_community_feed(
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    size: int = Query(default=10, ge=1, le=100, description="Jumlah item per halaman"),
    company: str | None = Query(default=None, description="Filter by company name (partial match)"),
    scam_category: str | None = Query(default=None, description="Filter by scam category"),
    min_scam: float | None = Query(default=None, ge=0, le=100, description="Minimum scam percentage"),
    max_scam: float | None = Query(default=None, ge=0, le=100, description="Maximum scam percentage"),
    search: str | None = Query(default=None, description="Search across job_title and company_name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Mengembalikan semua hasil yang dishare ke community (paginated, filterable).
    
    Endpoint ini publik - tidak memerlukan autentikasi.
    
    Filters:
    - company: Filter by company name (case-insensitive partial match)
    - scam_category: Filter by scam category (exact match)
    - min_scam: Minimum scam percentage
    - max_scam: Maximum scam percentage
    - search: Search across job_title and company_name (case-insensitive)
    """
    offset = (page - 1) * size
    
    # Base query: only shared results
    base_query = select(LokerCheck).where(LokerCheck.is_shared == True)
    
    # Apply filters
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
    if filters:
        for f in filters:
            count_query = count_query.where(f)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get paginated results with user relationship
    query = (
        select(LokerCheck)
        .options(selectinload(LokerCheck.user))
        .where(LokerCheck.is_shared == True)
        .order_by(LokerCheck.shared_at.desc())
        .offset(offset)
        .limit(size)
    )
    
    if filters:
        for f in filters:
            query = query.where(f)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    # Transform to response format with masked data
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report tidak ditemukan di community.",
        )
    
    logger.info(f"Community report detail accessed: report_id={report_id}")
    
    return CommunityReportResponse(**mask_sensitive_data(report))


# Share/Unshare endpoints (under jobs router, but documented here for reference)
# These endpoints are added to jobs.py for cleaner URL structure:
# - POST /api/v1/jobs/history/{check_id}/share
# - DELETE /api/v1/jobs/history/{check_id}/share