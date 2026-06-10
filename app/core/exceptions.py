"""Custom exception classes for standardized error handling."""
import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class AppException(HTTPException):
    """Base exception for application errors with standardized error format."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None
    ):
        self.error_code = error_code
        self.error_message = message
        self.error_details = details
        timestamp = datetime.utcnow().isoformat() + "Z"
        super().__init__(
            status_code=status_code,
            detail={
                "error": error_code,
                "message": message,
                "details": details,
                "timestamp": timestamp
            }
        )


# ========== Authentication & Authorization Exceptions ==========

class UnauthorizedException(AppException):
    """Exception for authentication errors (401)."""
    
    def __init__(
        self,
        message: str = "Autentikasi diperlukan. Silakan login terlebih dahulu."
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message
        )


class ForbiddenException(AppException):
    """Exception for authorization errors (403)."""
    
    def __init__(
        self,
        message: str = "Anda tidak memiliki akses ke resource ini."
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=message
        )


class TokenExpiredException(AppException):
    """Exception for expired token errors (401)."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            message="Token sudah kedaluwarsa. Silakan login kembali."
        )


class TokenInvalidException(AppException):
    """Exception for invalid token errors (401)."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_INVALID",
            message="Token tidak valid."
        )


# ========== Resource Exceptions ==========

class NotFoundException(AppException):
    """Exception for resource not found errors (404)."""
    
    def __init__(self, resource_type: str, resource_id: int | str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"{resource_type} dengan ID {resource_id} tidak ditemukan.",
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class ConflictException(AppException):
    """Exception for resource conflict errors (409)."""
    
    def __init__(
        self,
        message: str,
        existing_resource: str | None = None
    ):
        details = {"existing_resource": existing_resource} if existing_resource else None
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            message=message,
            details=details
        )


class GoneException(AppException):
    """Exception for resource permanently deleted errors (410)."""
    
    def __init__(self, resource_type: str):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            error_code="GONE",
            message=f"{resource_type} sudah dihapus secara permanen."
        )


# ========== Validation & Request Exceptions ==========

class BadRequestException(AppException):
    """Exception for bad request errors (400)."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None
    ):
        details = {"field": field} if field else None
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            message=message,
            details=details
        )


class ValidationException(AppException):
    """Exception for validation errors (422)."""
    
    def __init__(self, field_errors: list[dict[str, str]]):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Validasi data gagal.",
            details={"field_errors": field_errors}
        )


# ========== File Upload Exceptions ==========

class FileTooLargeException(AppException):
    """Exception for file size limit errors (413)."""
    
    def __init__(self, max_size_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="FILE_TOO_LARGE",
            message=f"Ukuran file melebihi batas {max_size_mb} MB.",
            details={"max_size_mb": max_size_mb}
        )


class UnsupportedMediaTypeException(AppException):
    """Exception for unsupported content type errors (415)."""
    
    def __init__(self, content_type: str):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="UNSUPPORTED_MEDIA_TYPE",
            message=f"Format file '{content_type}' tidak didukung. Gunakan PNG atau JPG.",
            details={"content_type": content_type}
        )


class FileCorruptedException(AppException):
    """Exception for corrupted file errors (422)."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="FILE_CORRUPTED",
            message="File bukan gambar valid atau file gambar rusak."
        )


# ========== Rate Limiting Exceptions ==========

class RateLimitException(AppException):
    """Exception for rate limit errors (429)."""
    
    def __init__(self, retry_after_seconds: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message="Terlalu banyak request. Silakan coba lagi nanti.",
            details={"retry_after_seconds": retry_after_seconds}
        )


# ========== Business Logic Exceptions ==========

class DraftNotSubmittedException(AppException):
    """Exception when trying to share an unsubmitted draft."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DRAFT_NOT_SUBMITTED",
            message="Hasil harus di-submit terlebih dahulu sebelum dishare."
        )


class AlreadySharedException(AppException):
    """Exception when trying to share an already shared resource."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="ALREADY_SHARED",
            message="Hasil sudah dishare ke community."
        )


class NotSharedException(AppException):
    """Exception when trying to unshare a non-shared resource."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="NOT_SHARED",
            message="Hasil belum dishare ke community."
        )


class DraftAlreadySubmittedException(AppException):
    """Exception when trying to modify an already submitted draft."""
    
    def __init__(
        self,
        action: str = "diedit"
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DRAFT_ALREADY_SUBMITTED",
            message=f"Draft sudah di-submit dan tidak bisa {action}."
        )


# ========== Server Exceptions ==========

class InternalServerException(AppException):
    """Exception for internal server errors (500)."""
    
    def __init__(
        self,
        message: str = "Terjadi kesalahan pada server. Silakan coba lagi nanti."
    ):
        # Security: Don't expose internal error details to client
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=message
        )


class ServiceUnavailableException(AppException):
    """Exception for service unavailable errors (503)."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            message="Layanan sedang tidak tersedia. Silakan coba lagi nanti."
        )


# ========== Exception Handlers ==========

async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    field_errors = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field_path = ".".join(str(loc) if loc else "unknown")
        field_errors.append({
            "field": field_path,
            "message": error.get("msg", "Validation error")
        })
    
    logger.warning(f"Validation error: {field_errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Validasi data gagal.",
            "details": {"field_errors": field_errors},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


async def database_exception_handler(request, exc: Exception):
    """Handle database errors."""
    logger.error(f"Database error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Terjadi kesalahan pada database. Silakan coba lagi nanti.",
            "details": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


async def general_exception_handler(request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Terjadi kesalahan pada server. Silakan coba lagi nanti.",
            "details": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )