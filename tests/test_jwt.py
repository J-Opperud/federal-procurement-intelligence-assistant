
import pytest

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
