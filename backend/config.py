"""Application configuration."""

import os


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Yahoo OAuth - read directly from environment
        self.yahoo_client_id = os.environ.get("YAHOO_CLIENT_ID", "")
        self.yahoo_client_secret = os.environ.get("YAHOO_CLIENT_SECRET", "")
        self.yahoo_redirect_uri = os.environ.get(
            "YAHOO_REDIRECT_URI",
            "http://localhost:8000/auth/callback"
        )

        # App settings
        self.app_name = "Fantasy Football Report Generator"
        self.app_url = os.environ.get("APP_URL", "http://localhost:8000")
        self.secret_key = os.environ.get(
            "SECRET_KEY",
            "change-this-in-production-to-a-random-string"
        )

        # File storage
        self.reports_dir = os.environ.get("REPORTS_DIR", "./reports")
        self.max_report_age_hours = 24

        # Debug: print what we loaded
        print(f"[CONFIG] YAHOO_CLIENT_ID: {self.yahoo_client_id[:20]}..." if self.yahoo_client_id else "[CONFIG] YAHOO_CLIENT_ID: NOT SET")
        print(f"[CONFIG] YAHOO_REDIRECT_URI: {self.yahoo_redirect_uri}")


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
