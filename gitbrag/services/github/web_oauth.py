"""Web-based OAuth flow for GitHub authentication.

This module provides OAuth functionality for web applications,
using FastAPI routes instead of a local callback server.
"""

import secrets
from logging import getLogger
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

logger = getLogger(__name__)


class WebOAuthFlow:
    """Handle GitHub App OAuth authentication flow for web applications."""

    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

    def __init__(self, client_id: str, client_secret: SecretStr, callback_url: str) -> None:
        """Initialize web OAuth flow handler.

        Args:
            client_id: GitHub App client ID
            client_secret: GitHub App client secret
            callback_url: Full callback URL (e.g., https://yourdomain.com/auth/callback)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url

    def generate_state(self) -> str:
        """Generate a secure random state parameter for CSRF protection.

        Returns:
            URL-safe random string
        """
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str, scopes: list[str] | None = None) -> str:
        """Build GitHub OAuth authorization URL.

        Args:
            state: CSRF state parameter (should be stored in session)
            scopes: List of OAuth scopes to request (defaults to read:user)

        Returns:
            Authorization URL for user to visit
        """
        if scopes is None:
            scopes = ["read:user"]  # Minimal scope for public data access

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(scopes),
            "state": state,
        }

        auth_url = f"{self.GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        logger.info(f"Generated OAuth authorization URL with scopes: {', '.join(scopes)}")

        return auth_url

    async def exchange_code_for_token(self, code: str) -> SecretStr:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Access token as SecretStr

        Raises:
            ValueError: If token exchange fails
            httpx.HTTPError: If HTTP request fails
        """
        logger.info("Exchanging authorization code for access token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret.get_secret_value(),
                    "code": code,
                    "redirect_uri": self.callback_url,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed with status {response.status_code}: {response.text}")
                raise ValueError(f"Token exchange failed: HTTP {response.status_code}")

            data = response.json()

            if "error" in data:
                error_desc = data.get("error_description", data["error"])
                logger.error(f"Token exchange error: {error_desc}")
                raise ValueError(f"Token exchange error: {error_desc}")

            if "access_token" not in data:
                logger.error("No access token in response")
                raise ValueError("No access token in response")

            logger.info("Successfully obtained access token")
            return SecretStr(data["access_token"])
