"""Test utilities and factories for CekLoker Backend API."""
import io
from pathlib import Path
import shutil
from PIL import Image


def generate_test_image(
    width: int = 800,
    height: int = 600,
    format: str = "JPEG"
) -> bytes:
    """Generate test image bytes.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        format: Image format (JPEG or PNG)
    
    Returns:
        bytes: Image data as bytes
    """
    image = Image.new("RGB", (width, height), color=(73, 109, 137))
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()


def cleanup_test_uploads() -> None:
    """Clean up test upload directories after tests."""
    test_dirs = ["uploads/loker", "uploads/profile"]
    for dir_path in test_dirs:
        path = Path(dir_path)
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


class TestUserFactory:
    """Factory for creating test user data."""
    
    @staticmethod
    def create_dict(
        email: str = "test@example.com",
        username: str = "testuser",
        password: str = "TestPassword123!",
        full_name: str = "Test User"
    ) -> dict:
        """Create test user data dictionary."""
        return {
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        }


class TestOCRDataFactory:
    """Factory for creating test OCR data."""
    
    @staticmethod
    def create_valid() -> dict:
        """Create valid OCR data for legitimate job posting."""
        return {
            "job_title": "Software Engineer",
            "job_type": "Full-time",
            "company_name": "PT Contoh Indonesia",
            "company_email": "hr@contoh.co.id",
            "phone_number": "081234567890",
            "salary": "Rp 5.000.000 - 8.000.000",
            "description": "Lowongan pekerjaan untuk fresh graduate",
        }
    
    @staticmethod
    def create_suspicious() -> dict:
        """Create suspicious OCR data for scam detection testing."""
        return {
            "job_title": "Kerja dari Rumah",
            "job_type": "Freelance",
            "company_name": "KlikDisini.com",
            "company_email": "online@job4u.xyz",
            "phone_number": "085211112222",
            "salary": "Rp 15.000.000 - 50.000.000",
            "description": "Tanpa interview, langsung kerja!",
        }
    
    @staticmethod
    def create_minimal() -> dict:
        """Create minimal OCR data with only required fields."""
        return {
            "job_title": "Data Entry",
            "company_name": "PT ABC",
        }


class TestLokerCheckFactory:
    """Factory for creating test loker check records."""
    
    @staticmethod
    def create_dict(
        user_id: int,
        is_draft: bool = False,
        is_shared: bool = False,
        **kwargs
    ) -> dict:
        """Create test loker check data dictionary."""
        base = TestOCRDataFactory.create_valid()
        base.update({
            "user_id": user_id,
            "is_draft": is_draft,
            "is_shared": is_shared,
            "scam_percentage": 15.0 if not is_draft else None,
            "scam_category": "Aman" if not is_draft else None,
            "scam_reason": "Informasi lengkap dan transparan" if not is_draft else None,
            "raw_ocr_text": "Sample OCR text for testing purposes",
            "ocr_data": base,
        })
        base.update(kwargs)
        return base