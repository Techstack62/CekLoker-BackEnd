from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class LokerCheck(Base):
    __tablename__ = "loker_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # OCR extracted fields (kept for backwards compatibility, overridden by ocr_data on submit)
    job_title = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    info_source = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    company_email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    salary = Column(String, nullable=True)
    raw_ocr_text = Column(Text, nullable=True)

    # New: Structured OCR data in JSON format
    ocr_data = Column(JSON, nullable=True)

    # Scam analysis result
    scam_percentage = Column(Float, nullable=True)
    scam_category = Column(String, nullable=True)
    scam_reason = Column(Text, nullable=True)

    # Image reference
    image_filename = Column(String, nullable=True)

    # Draft status for two-stage workflow
    is_draft = Column(Boolean, default=True, nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="loker_checks")

    @property
    def image_url(self) -> str | None:
        """Relative API URL to access this check's uploaded image."""
        if not self.image_filename:
            return None
        return f"/api/v1/jobs/history/{self.id}/image"
