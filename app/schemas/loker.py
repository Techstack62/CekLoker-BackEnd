from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OCRData(BaseModel):
    """Structured OCR extraction result."""
    job_title: Optional[str] = None
    job_type: Optional[str] = None
    info_source: Optional[str] = None
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    phone_number: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None


class OCRDataUpdate(BaseModel):
    """Schema for user to update/correct OCR data."""
    job_title: Optional[str] = Field(None, max_length=200)
    job_type: Optional[str] = Field(None, max_length=100)
    info_source: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)
    company_email: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    salary: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)


class OCRReviewRequest(BaseModel):
    """Request to update/edit OCR draft data."""
    ocr_data: OCRDataUpdate


class OCRResultResponse(BaseModel):
    """Response after OCR extraction - returns for user review."""
    id: int
    image_filename: str
    raw_text: str
    ocr_data: OCRData
    is_draft: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DraftListResponse(BaseModel):
    """Paginated list of drafts."""
    total: int
    page: int
    size: int
    results: list[OCRResultResponse]


class LokerCheckResponse(BaseModel):
    """Complete check response after scam analysis."""
    id: int
    user_id: int
    job_title: Optional[str] = None
    job_type: Optional[str] = None
    info_source: Optional[str] = None
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    phone_number: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    ocr_data: Optional[dict[str, Any]] = None
    scam_percentage: Optional[float] = None
    scam_category: Optional[str] = None
    scam_reason: Optional[str] = None
    image_filename: Optional[str] = None
    image_url: Optional[str] = None
    is_draft: bool
    submitted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LokerCheckSummary(BaseModel):
    """Lightweight summary used in paginated history list."""
    id: int
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    scam_percentage: Optional[float] = None
    scam_category: Optional[str] = None
    is_draft: bool
    image_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    """Paginated history list (submitted checks only)."""
    total: int
    page: int
    size: int
    results: list[LokerCheckSummary]