
from app.config import Settings


def test_default_database_url_uses_sqlite(tmp_path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
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
    )

    assert settings.get_database_url() == custom_url
