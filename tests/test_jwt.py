
import pytest

import jwt

from datetime import datetime, timezone

from app.config import settings

from app.utils.security import create_access_token, decode_access_token


def test_access_token_contains_user_identity():
    token = create_access_token(user_id=123)

    payload = decode_access_token(token)

    assert payload["sub"] == "123"


def test_invalid_access_token_is_rejected():
    with pytest.raises(ValueError):
        decode_access_token("not-a-valid-token")


def test_expired_access_token_is_rejected():
    token = create_access_token(
        user_id=123,
        expires_seconds=-1,
    )

    with pytest.raises(ValueError):
        decode_access_token(token)

def test_access_token_uses_configured_algorithm():
    token = create_access_token(user_id=123)

    header = jwt.get_unverified_header(token)

    assert header["alg"] == settings.jwt_algorithm


def test_access_token_uses_configured_expiration():
    token = create_access_token(user_id=123)

    payload = decode_access_token(token)
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    expected_seconds = settings.access_token_expire_minutes * 60

    assert int((expires_at - issued_at).total_seconds()) == expected_seconds
