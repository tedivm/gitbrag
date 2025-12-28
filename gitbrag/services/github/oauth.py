import asyncio
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging import getLogger
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from pydantic import SecretStr

logger = getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    # Type: ignore due to BaseHTTPRequestHandler server attribute type limitations
    server: "OAuthCallbackServer"  # type: ignore[assignment]

    def do_GET(self) -> None:
        """Handle GET request from OAuth callback."""
        parsed = urlparse(self.path)

        if parsed.path != "/callback":
            self.send_error(404, "Not Found")
            return

        query_params = parse_qs(parsed.query)
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        error = query_params.get("error", [None])[0]

        if error:
            self.server.error = error
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Authorization Failed</h1><p>Error: {error}</p></body></html>".encode())
            return

        if not code or not state:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Invalid callback</h1></body></html>")
            return

        if state != self.server.state:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Invalid state parameter</h1></body></html>")
            return

        self.server.code = code
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authorization Successful!</h1>"
            b"<p>You can close this window and return to the terminal.</p></body></html>"
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP server logging."""
        pass


class OAuthCallbackServer:
    """Local HTTP server to receive OAuth callback."""

    def __init__(self, port: int = 8080) -> None:
        """Initialize callback server.

        Args:
            port: Port number for the callback server
        """
        self.port = port
        self.code: str | None = None
        self.error: str | None = None
        self.state: str = secrets.token_urlsafe(32)
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None

    async def start(self, timeout: int = 300) -> str:
        """Start server and wait for authorization code.

        Args:
            timeout: Maximum seconds to wait for callback

        Returns:
            Authorization code from OAuth callback

        Raises:
            TimeoutError: If authorization not completed within timeout
            ValueError: If OAuth callback contains an error
        """
        # Create server
        self.server = HTTPServer(("localhost", self.port), OAuthCallbackHandler)
        self.server.code = None  # type: ignore
        self.server.error = None  # type: ignore
        self.server.state = self.state  # type: ignore

        # Start server in background thread
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        logger.info(f"OAuth callback server started on port {self.port}")

        # Wait for callback with timeout
        start_time = asyncio.get_event_loop().time()
        while self.server.code is None and self.server.error is None:  # type: ignore
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.stop()
                raise TimeoutError("OAuth authorization timed out")
            await asyncio.sleep(0.5)

        self.stop()

        if self.server.error:  # type: ignore[attr-defined]
            raise ValueError(f"OAuth authorization failed: {self.server.error}")  # type: ignore[attr-defined]

        if not self.server.code:  # type: ignore[attr-defined]
            raise ValueError("No authorization code received")

        code: str = self.server.code  # type: ignore[attr-defined]
        return code

    def stop(self) -> None:
        """Stop callback server."""
        if self.server:
            logger.info("Stopping OAuth callback server")
            self.server.shutdown()
            self.server = None
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None


class GitHubOAuthFlow:
    """Handle GitHub App OAuth authentication flow."""

    GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

    def __init__(self, client_id: str, client_secret: SecretStr, callback_port: int = 8080) -> None:
        """Initialize OAuth flow handler.

        Args:
            client_id: GitHub App client ID
            client_secret: GitHub App client secret
            callback_port: Port for local callback server
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_port = callback_port
        self.callback_server: OAuthCallbackServer | None = None

    async def initiate_flow(self, scopes: list[str] | None = None) -> str:
        """Start OAuth flow and return authorization URL.

        Args:
            scopes: List of OAuth scopes to request (defaults to repo access)

        Returns:
            Authorization URL for user to visit
        """
        if scopes is None:
            scopes = ["repo", "user"]

        self.callback_server = OAuthCallbackServer(port=self.callback_port)

        params = {
            "client_id": self.client_id,
            "redirect_uri": f"http://localhost:{self.callback_port}/callback",
            "scope": " ".join(scopes),
            "state": self.callback_server.state,
        }

        auth_url = f"{self.GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
        logger.info(f"Opening browser for OAuth authorization with scopes: {', '.join(scopes)}")

        # Open browser for user authorization
        webbrowser.open(auth_url)

        return auth_url

    async def complete_flow(self) -> str:
        """Wait for callback and exchange authorization code for access token.

        Returns:
            Access token for GitHub API

        Raises:
            ValueError: If OAuth flow not initiated or exchange fails
        """
        if not self.callback_server:
            raise ValueError("OAuth flow not initiated. Call initiate_flow() first.")

        # Wait for authorization code from callback
        code = await self.callback_server.start()

        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret.get_secret_value(),
                    "code": code,
                    "redirect_uri": f"http://localhost:{self.callback_port}/callback",
                },
            )

            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")

            data = response.json()

            if "error" in data:
                raise ValueError(f"Token exchange error: {data.get('error_description', data['error'])}")

            if "access_token" not in data:
                raise ValueError("No access token in response")

            token: str = data["access_token"]
            return token

    async def authenticate(self, scopes: list[str] | None = None) -> str:
        """Complete OAuth flow in one call (initiate + complete).

        Args:
            scopes: List of OAuth scopes to request (defaults to repo access)

        Returns:
            Access token for GitHub API

        Raises:
            ValueError: If OAuth flow fails
        """
        await self.initiate_flow(scopes=scopes)
        return await self.complete_flow()
