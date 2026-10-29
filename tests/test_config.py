
from app.config import Settings

import pytest

from pydantic import ValidationError

TEST_JWT_SECRET = "test-only-secret-key-with-at-least-32-chars"

TEST_SAM_API_KEY = "mock-sam-api-key-for-tests"

def test_default_database_url_uses_sqlite(tmp_path):

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        jwt_secret_key="test-only-secret-key-with-at-least-32-chars",
        TEST_SAM_API_KEY = "mock-sam-api-key-for-tests"
    )

    assert settings.get_database_url() == (
        f"sqlite:///{(tmp_path / 'scout.db').as_posix()}"
    )


def test_explicit_database_url_takes_precedence(tmp_path):
    custom_url = "sqlite:///custom.db"

    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        database_url=custom_url,
        jwt_secret_key="test-only-secret-key-with-at-least-32-chars",
        TEST_SAM_API_KEY = "mock-sam-api-key-for-tests"
    )

    assert settings.get_database_url() == custom_url


def test_jwt_secret_is_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raises= False)
    with pytest.raises(ValidationError):
    
        Settings(_env_file=None,
                 TEST_SAM_API_KEY = "mock-sam-api-key-for-tests",)


def test_jwt_secret_must_be_at_least_32_characters():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_secret_key="too-short",
            TEST_SAM_API_KEY = "mock-sam-api-key-for-tests",
        )


def test_token_expiration_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_secret_key="test-only-secret-key-with-at-least-32-chars",
            access_token_expire_minutes=0,
            TEST_SAM_API_KEY = "mock-sam-api-key-for-tests",
        )
def test_sam_api_key_is_required(monkeypatch):
    monkeypatch.delenv("SAM_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_secret_key=TEST_JWT_SECRET,
        )
