"""
app/config.py — Configuration and Settings via Pydantic
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load .env from project root and backend dir
_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent
load_dotenv(_root_dir / ".env")
load_dotenv(_backend_dir / ".env")



class Settings(BaseSettings):
    # API & CORS
    cors_origins: list[str] = ["*"]
    api_prefix: str = "/api"

    # Database (PostgreSQL with asyncpg)
    database_url: str = ""
    database_echo: bool = False

    # Authentication & Security
    jwt_secret_key: str = "startupscrape-secret-key-production-change-32char"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Pipeline & Third-party integrations
    treg_token: Optional[str] = None
    browserbase_api_key: Optional[str] = None
    browserbase_project_id: Optional[str] = None
    browserbase_linkedin_context_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.6-flash"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
