"""Application configuration."""

import os


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Debug: Show all YAHOO env vars
        print("[CONFIG] === Environment Variable Debug ===")
        for key, value in os.environ.items():
            if "YAHOO" in key.upper():
                print(f"[CONFIG] Found env var: {key}={value[:30] if len(value) > 30 else value}...")

        # Yahoo OAuth - read directly from environment
        self.yahoo_client_id = os.environ.get("YAHOO_CLIENT_ID", "")
        self.yahoo_client_secret = os.environ.get("YAHOO_CLIENT_SECRET", "")

        # Get redirect URI with detailed debug
        raw_redirect = os.environ.get("YAHOO_REDIRECT_URI")
        print(f"[CONFIG] Raw YAHOO_REDIRECT_URI from os.environ.get: '{raw_redirect}' (type: {type(raw_redirect)})")

        if raw_redirect is None:
            print("[CONFIG] YAHOO_REDIRECT_URI is None, using default")
            self.yahoo_redirect_uri = "http://localhost:8000/auth/callback"
        elif raw_redirect.strip() == "":
            print("[CONFIG] YAHOO_REDIRECT_URI is empty string, using default")
            self.yahoo_redirect_uri = "http://localhost:8000/auth/callback"
        else:
            self.yahoo_redirect_uri = raw_redirect.strip()

        print(f"[CONFIG] Final yahoo_redirect_uri: '{self.yahoo_redirect_uri}'")

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
        print(f"[CONFIG] === End Config Debug ===")


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
