"""Unit tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserLogin, UserUpdate
from app.schemas.loker import (
    OCRData,
    OCRDataUpdate,
    ShareToCommunityRequest,
)


class TestUserSchemas:
    """Unit tests for User schemas."""

    def test_user_create_valid(self):
        """Test valid user creation schema."""
        data = UserCreate(
            email="test@example.com",
            password="Password123!",
            full_name="Test User",
        )
        assert data.email == "test@example.com"
        assert data.password == "Password123!"

    def test_user_create_invalid_email(self):
        """Test user creation with invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid-email",
                password="Password123!",
            )
        assert "email" in str(exc_info.value).lower()

    def test_user_create_short_password(self):
        """Test user creation with short password raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="short",
            )
        assert "password" in str(exc_info.value).lower()

    def test_user_create_missing_required_fields(self):
        """Test user creation with missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com")

    def test_user_update_partial(self):
        """Test partial user update works correctly."""
        update = UserUpdate(full_name="New Name")
        assert update.full_name == "New Name"
        assert update.model_dump(exclude_unset=True) == {"full_name": "New Name"}

    def test_user_update_empty(self):
        """Test empty user update works correctly."""
        update = UserUpdate()
        assert update.model_dump(exclude_unset=True) == {}


class TestOCRSchemas:
    """Unit tests for OCR schemas."""

    def test_ocr_data_valid(self):
        """Test valid OCR data creation."""
        data = OCRData(
            job_title="Software Engineer",
            company_name="PT Contoh",
            company_email="hr@contoh.com",
        )
        assert data.job_title == "Software Engineer"
        assert data.company_name == "PT Contoh"

    def test_ocr_data_all_optional(self):
        """Test OCR data with no fields works correctly."""
        data = OCRData()
        assert data.job_title is None
        assert data.company_name is None

    def test_ocr_data_update_with_max_lengths(self):
        """Test OCR data update respects max lengths."""
        with pytest.raises(ValidationError):
            OCRDataUpdate(job_title="x" * 201)

    def test_share_request_default(self):
        """Test share request default values."""
        request = ShareToCommunityRequest()
        assert request.anonymous is False

    def test_share_request_anonymous_true(self):
        """Test share request with anonymous=True."""
        request = ShareToCommunityRequest(anonymous=True)
        assert request.anonymous is True