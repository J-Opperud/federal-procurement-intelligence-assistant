
"""Shared error translation for external HTTP services."""

import httpx

from app.utils.exceptions import AppException


class ExternalServiceException(AppException):
    """A safe, standardized error from an external service."""


def translate_http_error(exc: Exception) -> ExternalServiceException:
    """Translate HTTPX failures into safe application exceptions."""

    if isinstance(exc, httpx.TimeoutException):
        return ExternalServiceException(
            detail="An external service timed out. Try again later.",
            status_code=504,
            code="EXTERNAL_SERVICE_TIMEOUT",
        )

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code

        if status == 429:
            return ExternalServiceException(
                detail="An external service rate limit was reached.",
                status_code=429,
                code="EXTERNAL_SERVICE_RATE_LIMIT",
            )

        if status >= 500:
            return ExternalServiceException(
                detail="An external service is temporarily unavailable.",
                status_code=502,
                code="EXTERNAL_SERVICE_UNAVAILABLE",
            )

        return ExternalServiceException(
            detail="An external service rejected the request.",
            status_code=502,
            code="EXTERNAL_SERVICE_REQUEST_FAILED",
        )

    if isinstance(exc, httpx.RequestError):
        return ExternalServiceException(
            detail="Unable to connect to an external service.",
            status_code=502,
            code="EXTERNAL_SERVICE_CONNECTION_FAILED",
        )

    return ExternalServiceException(
        detail="An external service request failed.",
        status_code=502,
        code="EXTERNAL_SERVICE_ERROR",
    )
