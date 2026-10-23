from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """Validate registration input."""

    username: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        )
    password: str = Field(
        min_length=15,
        max_length=128,
        )
    @field_validator("username", mode="before")
    @classmethod

    def normalize_username(cls, value: str) -> str:
        """Trim whitespace and normalize username casing."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserLogin(BaseModel):
    """Validate login input."""

    username: str = Field(
        min_length=1,
        max_length=128,
        )
    password: str = Field(
        min_length=1,
        )

class UserResponse(BaseModel):
    """Expose safe, public user information."""

    model_config = ConfigDict(from_attributes=True)


    id: int
    username: str
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    """Return an access token to the client."""

    access_token: str
    token_type: str = "bearer"

