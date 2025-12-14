"""GitHub authentication and client factory."""

from logging import getLogger

from pydantic import SecretStr

from gitbrag.conf.github import GitHubAuthType, GitHubSettings

from .client import GitHubAPIClient
from .oauth import GitHubOAuthFlow

logger = getLogger(__name__)


class GitHubClient:
    """Factory for creating authenticated GitHub API clients."""

    def __init__(self, settings: GitHubSettings | None = None, token_override: str | None = None) -> None:
        """Initialize with settings.

        Args:
            settings: GitHub settings (defaults to global settings)
            token_override: Optional PAT token to override settings
        """
        if settings is None:
            from gitbrag.settings import settings as global_settings

            settings = global_settings

        self.settings = settings
        self.token_override = token_override

    async def get_authenticated_client(self) -> GitHubAPIClient:
        """Return authenticated GitHub API client.

        For PAT: Use token directly.
        For GitHub App: Complete OAuth flow if needed, use user access token.

        Returns:
            Authenticated GitHub API client

        Raises:
            ValueError: If authentication fails or configuration is invalid
        """
        # Use token override if provided
        if self.token_override:
            logger.info("Using token override for authentication")
            token = SecretStr(self.token_override)
            return GitHubAPIClient(token)

        # Handle PAT authentication
        if self.settings.github_auth_type == GitHubAuthType.PAT:
            if not self.settings.github_token:
                raise ValueError("GitHub PAT token not configured")

            logger.info("Using PAT for authentication")
            return GitHubAPIClient(self.settings.github_token)

        # Handle GitHub App OAuth authentication
        if self.settings.github_auth_type == GitHubAuthType.GITHUB_APP:
            if not self.settings.github_app_client_id or not self.settings.github_app_client_secret:
                raise ValueError("GitHub App credentials not configured")

            logger.info("Starting GitHub App OAuth flow")
            oauth_flow = GitHubOAuthFlow(
                client_id=self.settings.github_app_client_id,
                client_secret=self.settings.github_app_client_secret,
                callback_port=self.settings.github_oauth_callback_port,
            )

            access_token = await oauth_flow.authenticate()
            return GitHubAPIClient(SecretStr(access_token))

        raise ValueError(f"Unsupported authentication type: {self.settings.github_auth_type}")
