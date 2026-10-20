
class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        code: str = "APP_ERROR",
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.code = code
        super().__init__(detail)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: int | str) -> None:
        super().__init__(
            detail=f"{resource} with id {resource_id} not found.",
            status_code=404,
            code="RESOURCE_NOT_FOUND",
        )


class DuplicateException(AppException):
    """Raised when a resource conflicts with an existing record."""

    def __init__(
        self,
        resource: str,
        field: str,
        value: str | None = None,
        *,
        code: str = "RESOURCE_DUPLICATE",
        ) -> None:
        detail = f"{resource} with that {field} already exists."
        
        super().__init__(
            detail=detail,
            status_code=409,
            code=code,
            )


class BadRequestException(AppException):
    """Raised when a request violates business rules."""

    def __init__(
        self,
        detail: str,
        code: str = "BAD_REQUEST",
        ) -> None:
        
        super().__init__(
            detail=detail,
            status_code=400,
            code=code,
            )


class UnauthorizedException(AppException):
    """Raised when authentication is missing or invalid."""

    def __init__(
        self,
        detail: str = "Authentication required.",
        code: str = "AUTHENTICATION_REQUIRED",
        ) -> None:
        
        super().__init__(
            detail=detail,
            status_code=401,
            code=code,
            )


class ForbiddenException(AppException):
    """Raised when a user lacks permission for an action."""

    def __init__(
        self,
        detail: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
        ) -> None:
        
        super().__init__(
            detail=detail,
            status_code=403,
            code=code,
            )
