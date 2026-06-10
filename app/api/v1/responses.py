"""Response helper functions for clean Swagger documentation."""
from typing import Any, Optional


def build_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    """
    Build a response dict from a list of status codes.
    
    This is a simple helper to combine pre-defined responses.
    Import the response constants from app.schemas.responses instead.
    """
    from app.schemas import responses as r
    
    result = {}
    mapping = {
        400: r.BAD_REQUEST_RESPONSE,
        401: r.UNAUTHORIZED_RESPONSE,
        403: r.FORBIDDEN_RESPONSE,
        404: r.NOT_FOUND_RESPONSE,
        409: r.CONFLICT_RESPONSE,
        413: r.FILE_TOO_LARGE_RESPONSE,
        415: r.UNSUPPORTED_MEDIA_TYPE_RESPONSE,
        429: r.RATE_LIMIT_RESPONSE,
        500: r.INTERNAL_ERROR_RESPONSE,
    }
    
    for code in status_codes:
        if code in mapping:
            result.update(mapping[code])
    
    return result


def responses_401_403_404_500() -> dict[int, dict[str, Any]]:
    """Common responses for authenticated endpoints."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.NOT_FOUND_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_401_409_500() -> dict[int, dict[str, Any]]:
    """Responses for auth registration endpoint."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.CONFLICT_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_401_500() -> dict[int, dict[str, Any]]:
    """Responses for auth login endpoint."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_file_upload() -> dict[int, dict[str, Any]]:
    """Responses for file upload endpoints."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.NOT_FOUND_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.FILE_TOO_LARGE_RESPONSE,
        **r.UNSUPPORTED_MEDIA_TYPE_RESPONSE,
        **r.RATE_LIMIT_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_share() -> dict[int, dict[str, Any]]:
    """Responses for community share endpoints."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.NOT_FOUND_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.CONFLICT_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_profile() -> dict[int, dict[str, Any]]:
    """Responses for profile endpoints."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.NOT_FOUND_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.CONFLICT_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }


def responses_community() -> dict[int, dict[str, Any]]:
    """Responses for community endpoints."""
    from app.schemas import responses as r
    return {
        **r.UNAUTHORIZED_RESPONSE,
        **r.FORBIDDEN_RESPONSE,
        **r.NOT_FOUND_RESPONSE,
        **r.BAD_REQUEST_RESPONSE,
        **r.INTERNAL_ERROR_RESPONSE,
    }