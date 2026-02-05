"""Yahoo OAuth 2.0 authentication handling."""

import httpx
import base64
from urllib.parse import urlencode
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from config import get_settings


@dataclass
class YahooTokens:
    """Yahoo OAuth tokens."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "bearer"

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return datetime.utcnow() >= self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary for session storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "YahooTokens":
        """Create from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            token_type=data.get("token_type", "bearer"),
        )


class YahooOAuth:
    """Yahoo OAuth 2.0 client."""

    AUTHORIZE_URL = "https://api.login.yahoo.com/oauth2/request_auth"
    TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        """Get the Yahoo authorization URL."""
        # Debug: log the redirect URI being used
        print(f"[AUTH] Building OAuth URL with redirect_uri: '{self.settings.yahoo_redirect_uri}'")

        params = {
            "client_id": self.settings.yahoo_client_id,
            "redirect_uri": self.settings.yahoo_redirect_uri,
            "response_type": "code",
            "state": state,
        }
        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        print(f"[AUTH] Full OAuth URL: {url}")
        return url

    async def exchange_code(self, code: str) -> YahooTokens:
        """Exchange authorization code for tokens."""
        # Yahoo requires Basic auth with client credentials
        credentials = f"{self.settings.yahoo_client_id}:{self.settings.yahoo_client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.yahoo_redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            token_data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        return YahooTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=expires_at,
        )

    async def refresh_tokens(self, refresh_token: str) -> YahooTokens:
        """Refresh expired access token."""
        credentials = f"{self.settings.yahoo_client_id}:{self.settings.yahoo_client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            token_data = response.json()

        expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        return YahooTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_at=expires_at,
        )


yahoo_oauth = YahooOAuth()
