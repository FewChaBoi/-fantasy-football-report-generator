"""Application configuration."""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Yahoo OAuth - explicitly map to uppercase env vars
    yahoo_client_id: str = Field(default="", alias="YAHOO_CLIENT_ID")
    yahoo_client_secret: str = Field(default="", alias="YAHOO_CLIENT_SECRET")
    yahoo_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        alias="YAHOO_REDIRECT_URI"
    )

    # App settings
    app_name: str = "Fantasy Football Report Generator"
    app_url: str = Field(default="http://localhost:8000", alias="APP_URL")
    secret_key: str = Field(
        default="change-this-in-production-to-a-random-string",
        alias="SECRET_KEY"
    )

    # File storage
    reports_dir: str = Field(default="./reports", alias="REPORTS_DIR")
    max_report_age_hours: int = 24

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True


def get_settings() -> Settings:
    """Get settings instance (no caching to ensure env vars are read)."""
    return Settings()
