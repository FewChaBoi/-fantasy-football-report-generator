"""Application configuration."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Yahoo OAuth
    yahoo_client_id: str = ""
    yahoo_client_secret: str = ""
    yahoo_redirect_uri: str = "http://localhost:8000/auth/callback"

    # App settings
    app_name: str = "Fantasy Football Report Generator"
    app_url: str = "http://localhost:8000"
    secret_key: str = "change-this-in-production-to-a-random-string"

    # File storage
    reports_dir: str = "./reports"
    max_report_age_hours: int = 24

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
