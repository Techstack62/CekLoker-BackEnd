from pydantic import BaseModel
from datetime import datetime


class LokerCheckResponse(BaseModel):
    id: int
    user_id: int

    # OCR fields
    job_title: str | None = None
    job_type: str | None = None
    info_source: str | None = None
    company_name: str | None = None
    company_email: str | None = None
    phone_number: str | None = None
    description: str | None = None
    salary: str | None = None
    raw_ocr_text: str | None = None

    # Scam analysis
    scam_percentage: float | None = None
    scam_category: str | None = None
    scam_reason: str | None = None

    image_filename: str | None = None
    image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LokerCheckSummary(BaseModel):
    """Lightweight summary used in paginated history list."""
    id: int
    job_title: str | None = None
    company_name: str | None = None
    scam_percentage: float | None = None
    scam_category: str | None = None
    image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    total: int
    page: int
    size: int
    results: list[LokerCheckSummary]
