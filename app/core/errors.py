"""Error code constants for standardized API error responses."""

from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses.
    
    All error responses follow a consistent format with these error codes,
    making it easier for clients to handle errors programmatically.
    """
    
    # ========== Authentication & Authorization ==========
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # ========== Resource Errors ==========
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    GONE = "GONE"
    
    # ========== Validation Errors ==========
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # ========== File Upload Errors ==========
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    
    # ========== Rate Limiting ==========
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # ========== Business Logic Errors ==========
    DRAFT_NOT_SUBMITTED = "DRAFT_NOT_SUBMITTED"
    ALREADY_SHARED = "ALREADY_SHARED"
    NOT_SHARED = "NOT_SHARED"
    DRAFT_ALREADY_SUBMITTED = "DRAFT_ALREADY_SUBMITTED"
    
    # ========== Server Errors ==========
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


# HTTP Status Code mapping
HTTP_STATUS_MAP = {
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.GONE: 410,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.CONFLICT: 409,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
}