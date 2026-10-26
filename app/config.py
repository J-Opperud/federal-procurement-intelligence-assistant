from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Literal

from pydantic import Field


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

    SAM_API_KEY: str = Field(min_length=1)

    jwt_secret_key: str = Field(min_length=32)

    jwt_algorithm: Literal["HS256"] = "HS256"

    access_token_expire_minutes: int = Field(
        default=60,
        gt=0
    )
    # Semantic search and source-document indexing.
    chroma_persist_directory: Path | None = None

    chroma_collection_name: str = Field(
        default="sentinel_evidence",
        min_length=1,
        max_length=128,
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        min_length=1,
    )

    document_chunk_size: int = Field(
        default=300,
        ge=50,
        le=10_000
    )

    document_chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=9_999
    )

      
    retrieval_n_results: int = Field(
        default=6,
        gt=0,
    )

    retrieval_distance_threshold: float = Field(
        default=1.1,
        ge=0,
        le=2,
    ) 
        # Local Ollama answer generation.

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        min_length=1,
    )

    ollama_model: str = Field(
        default="llama3.2:latest",
        min_length=1,
    )

    ollama_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
    )

    def get_database_url(self) -> str:
        """Return the configured database URL or the default SQLite URL."""

        if self.database_url:
            return self.database_url

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        database_path = self.data_dir / "scout.db"

        return f"sqlite:///{database_path.as_posix()}"


settings = Settings()

if settings.document_chunk_overlap >= settings.document_chunk_size:

    raise ValueError(
        "DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_SIZE."
        )
