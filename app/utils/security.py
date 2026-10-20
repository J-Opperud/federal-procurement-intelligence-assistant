import jwt 

from pwdlib import PasswordHash

from app.config import settings

from datetime import datetime,timedelta, timezone

password_hash = PasswordHash.recommended()



def hash_password(password: str) -> str:
    """Hash a plaintext password for secure storage."""

    return password_hash.hash(password)


def verify_password(
        password: str,
        hash_password: str,
    ) -> bool:

    """Check a password against its stored hash."""

    return password_hash.verify(password, hash_password)

def create_access_token(
        user_id: int,
        expires_seconds: int | None = None,
    ) -> str:

    """Create a signed JWT for an authenticated user."""

    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY mustbe configured.")

    now = datetime.now(timezone.utc)
    expires_at = (
        now + timedelta(seconds=expires_seconds)
        if expires_seconds is not None
        else now + timedelta(
            minutes=settings.access_token_expire_minutes
            )
        )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        )


def decode_access_token(token: str) -> dict:
    """Validate a JWT and return its claims."""
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured.")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired access token.") from exc

    if not payload["sub"].isdigit() or int(payload["sub"]) < 1:
        raise ValueError("Invalid token subject.")

    return payload

