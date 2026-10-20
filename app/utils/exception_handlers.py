
from fastapi import Request

from fastapi.exceptions import RequestValidationError

from fastapi.responses import JSONResponse

from app.schemas.errors import ErrorResponse

from app.utils.exceptions import AppException


async def app_exception_handler(
    request: Request,
    exc: AppException,
    ) -> JSONResponse:
    """Convert application exceptions into consistent JSON responses."""

    response = ErrorResponse(
        error={
            "code": exc.code,
            "message": exc.detail,
            }
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(exclude_none=True),
        )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
    ) -> JSONResponse:
    """Return safe, structured details for invalid requests."""

    details = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
        ]

    response = ErrorResponse(
        error={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": details,
            }
        )

    return JSONResponse(
        status_code=422,
        content=response.model_dump(exclude_none=True),
        )
