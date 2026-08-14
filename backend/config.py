"""
Central configuration.
All settings come from .env — never hardcode secrets.
Import this anywhere: from config import settings
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from functools import lru_cache


class Settings(BaseSettings):

    # ── App ───────────────────────────────────────
    APP_NAME: str = "Document Intelligence Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000"

    # ── Database ──────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://docai:docai@localhost:5432/docai"

    # ── Redis ─────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"

    # ── Auth ──────────────────────────────────────
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080   # 7 days

    # ── AI ────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"               # "gemini" or "openai"
    LLM_MODEL: str = "gemini-1.5-flash"

    # ── Embedding ─────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMENSION: int = 1024

    # ── Reranker ──────────────────────────────────
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # ── Upload ────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors(cls, v: str) -> List[str]:
        return [origin.strip() for origin in v.split(",")]

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    lru_cache means this is only created once per process.
    """
    return Settings()


# Single importable instance
settings = get_settings()