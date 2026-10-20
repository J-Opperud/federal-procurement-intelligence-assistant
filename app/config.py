from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict



PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Centralized configuration for Sentinel Scout."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        )

    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str | None = None

    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    def get_database_url(self) -> str:
                """Return the configured database URL or the default SQLite URL."""

                if self.database_url:
                    return self.database_url

                self.data_dir.mkdir(
                       parents=True, exist_ok=True
                       )
                database_path = self.data_dir / "scout.db"

                return f"sqlite:///{database_path.as_posix()}"

settings = Settings()
