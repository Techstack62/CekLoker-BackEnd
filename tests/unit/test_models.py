"""Unit tests for database models."""
import pytest
from app.models.user import User
from app.models.loker_check import LokerCheck


class TestUserModel:
    """Unit tests for User model."""

    @pytest.mark.asyncio
    async def test_user_creation(self, db_session, test_user_data):
        """Test user can be created with valid data."""
        user = User(
            email=test_user_data["email"],
            username=test_user_data["username"],
            password_hash="$2b$12$hashedpassword",
            full_name=test_user_data["full_name"],
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == test_user_data["email"]
        assert user.username == test_user_data["username"]

    def test_user_default_values(self, test_user: User):
        """Test user has correct default values."""
        assert test_user.is_active is True
        assert test_user.is_verified is False
        assert test_user.profile_image is None

    def test_user_email_property(self, test_user: User):
        """Test user email property returns correct value."""
        assert "@" in test_user.email
        assert test_user.full_name is not None


class TestLokerCheckModel:
    """Unit tests for LokerCheck model."""

    @pytest.mark.asyncio
    async def test_loker_check_creation(self, db_session, test_user):
        """Test loker check can be created with valid data."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Software Engineer",
            company_name="PT Contoh",
            is_draft=True,
        )
        db_session.add(check)
        await db_session.commit()
        await db_session.refresh(check)
        
        assert check.id is not None
        assert check.is_draft is True
        assert check.is_shared is False
        assert check.user_id == test_user.id

    def test_masked_email_property(self, test_user: User):
        """Test email masking works correctly."""
        check = LokerCheck(
            user_id=test_user.id,
            company_email="johndoe@company.com",
        )
        
        masked = check.masked_email
        assert masked is not None
        assert "@company.com" in masked
        assert "johndoe" not in masked

    def test_masked_phone_property(self, test_user: User):
        """Test phone masking works correctly."""
        check = LokerCheck(
            user_id=test_user.id,
            phone_number="081234567890",
        )
        
        masked = check.masked_phone
        assert masked is not None
        assert "0812" not in masked
        assert "7890" in masked

    def test_image_url_property(self, test_user: User):
        """Test image URL generation."""
        check = LokerCheck(
            user_id=test_user.id,
            image_filename="test123.jpg",
        )
        
        url = check.image_url
        assert url is not None
        assert "/api/v1/jobs/history/" in url
        assert "image" in url

    def test_image_url_returns_none_without_filename(self, test_user: User):
        """Test image URL returns None when no filename."""
        check = LokerCheck(user_id=test_user.id)
        assert check.image_url is None

    def test_masked_email_short_username(self, test_user: User):
        """Test email masking with short username."""
        check = LokerCheck(
            user_id=test_user.id,
            company_email="ab@company.com",
        )
        
        masked = check.masked_email
        assert masked == "***@company.com"

    def test_masked_phone_short_number(self, test_user: User):
        """Test phone masking with short number."""
        check = LokerCheck(
            user_id=test_user.id,
            phone_number="1234",
        )
        
        masked = check.masked_phone
        assert masked == "***1234"

    @pytest.mark.asyncio
    async def test_loker_check_shared_status(self, db_session, test_user):
        """Test loker check sharing fields default correctly."""
        check = LokerCheck(
            user_id=test_user.id,
            job_title="Test Job",
            is_draft=False,
        )
        db_session.add(check)
        await db_session.commit()
        
        assert check.is_shared is False
        assert check.shared_at is None
        assert check.share_anonymous is False