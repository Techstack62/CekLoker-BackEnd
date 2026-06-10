"""Standardized error response schemas for Swagger documentation."""
from typing import Any, Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail structure."""
    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard error response model for Swagger."""
    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "NOT_FOUND",
                "message": "Resource dengan ID 123 tidak ditemukan.",
                "details": {"resource_type": "Draft", "resource_id": "123"},
                "timestamp": "2026-06-10T12:00:00Z"
            }
        }
    }


# ========== Common Error Response Schemas ==========

UNAUTHORIZED_RESPONSE = {
    401: {
        "description": "Unauthorized - Missing or invalid authentication token",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "UNAUTHORIZED",
                    "message": "Autentikasi diperlukan. Silakan login terlebih dahulu.",
                    "details": None,
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

FORBIDDEN_RESPONSE = {
    403: {
        "description": "Forbidden - Authenticated but not authorized for this action",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "FORBIDDEN",
                    "message": "Anda tidak memiliki akses ke resource ini.",
                    "details": None,
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

NOT_FOUND_RESPONSE = {
    404: {
        "description": "Not Found - Resource does not exist",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "NOT_FOUND",
                    "message": "Draft dengan ID 123 tidak ditemukan.",
                    "details": {"resource_type": "Draft", "resource_id": "123"},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

CONFLICT_RESPONSE = {
    409: {
        "description": "Conflict - Resource already exists or duplicate entry",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "CONFLICT",
                    "message": "Email sudah terdaftar. Silakan gunakan email lain.",
                    "details": {"existing_resource": "Email: user@example.com"},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

BAD_REQUEST_RESPONSE = {
    400: {
        "description": "Bad Request - Invalid request format or malformed logic",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "BAD_REQUEST",
                    "message": "Draft sudah di-submit dan tidak bisa diedit.",
                    "details": {"field": None},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

FILE_TOO_LARGE_RESPONSE = {
    413: {
        "description": "Payload Too Large - File size exceeds limit",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "FILE_TOO_LARGE",
                    "message": "Ukuran file melebihi batas 10 MB.",
                    "details": {"max_size_mb": 10},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

UNSUPPORTED_MEDIA_TYPE_RESPONSE = {
    415: {
        "description": "Unsupported Media Type - Content-Type not supported",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "UNSUPPORTED_MEDIA_TYPE",
                    "message": "Format file 'application/pdf' tidak didukung. Gunakan PNG atau JPG.",
                    "details": {"content_type": "application/pdf"},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

RATE_LIMIT_RESPONSE = {
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Terlalu banyak request. Silakan coba lagi nanti.",
                    "details": {"retry_after_seconds": 60},
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

INTERNAL_ERROR_RESPONSE = {
    500: {
        "description": "Internal Server Error - Unexpected server error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Terjadi kesalahan pada server. Silakan coba lagi nanti.",
                    "details": None,
                    "timestamp": "2026-06-10T12:00:00Z"
                }
            }
        }
    }
}

# ========== Pre-built Response Combinations ==========

AUTH_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    **FORBIDDEN_RESPONSE,
    **CONFLICT_RESPONSE,
    **BAD_REQUEST_RESPONSE,
    **INTERNAL_ERROR_RESPONSE,
}

AUTHENTICATED_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    **FORBIDDEN_RESPONSE,
    **NOT_FOUND_RESPONSE,
    **BAD_REQUEST_RESPONSE,
    **INTERNAL_ERROR_RESPONSE,
}

FILE_UPLOAD_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    **FORBIDDEN_RESPONSE,
    **NOT_FOUND_RESPONSE,
    **BAD_REQUEST_RESPONSE,
    **FILE_TOO_LARGE_RESPONSE,
    **UNSUPPORTED_MEDIA_TYPE_RESPONSE,
    **RATE_LIMIT_RESPONSE,
    **INTERNAL_ERROR_RESPONSE,
}

SHARE_RESPONSES = {
    **UNAUTHORIZED_RESPONSE,
    **FORBIDDEN_RESPONSE,
    **NOT_FOUND_RESPONSE,
    **BAD_REQUEST_RESPONSE,
    **CONFLICT_RESPONSE,
    **INTERNAL_ERROR_RESPONSE,
}