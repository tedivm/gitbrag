from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from gitbrag.conf.github import GitHubAuthType, GitHubSettings
from gitbrag.services.github.auth import GitHubClient


@pytest.fixture
def pat_settings() -> GitHubSettings:
    """Create test settings with PAT authentication."""
    return GitHubSettings(
        github_auth_type=GitHubAuthType.PAT,
        github_token=SecretStr("test_pat_token"),
    )


@pytest.fixture
def github_app_settings() -> GitHubSettings:
    """Create test settings with GitHub App authentication."""
    return GitHubSettings(
        github_auth_type=GitHubAuthType.GITHUB_APP,
        github_app_client_id="test_client_id",
        github_app_client_secret=SecretStr("test_client_secret"),
        github_oauth_callback_port=8080,
    )


@pytest.mark.asyncio
async def test_pat_client_creation(pat_settings: GitHubSettings) -> None:
    """Test creating GitHub client with PAT authentication."""
    with patch("gitbrag.services.github.auth.GitHubAPIClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        client = GitHubClient(settings=pat_settings)
        github = await client.get_authenticated_client()

        assert github is not None
        assert github == mock_client_instance
        # Verify GitHubAPIClient was created with token (positional argument)
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        assert call_args[0][0] == pat_settings.github_token


@pytest.mark.asyncio
async def test_token_override(pat_settings: GitHubSettings) -> None:
    """Test using token override instead of settings."""
    with patch("gitbrag.services.github.auth.GitHubAPIClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        override_token = "override_token"
        client = GitHubClient(settings=pat_settings, token_override=override_token)
        await client.get_authenticated_client()

        # Verify GitHubAPIClient was created with the override token (positional argument)
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        # Token override is wrapped in SecretStr
        assert call_args[0][0].get_secret_value() == override_token


@pytest.mark.asyncio
async def test_github_app_oauth_flow(github_app_settings: GitHubSettings) -> None:
    """Test GitHub App OAuth authentication flow."""
    with (
        patch("gitbrag.services.github.auth.GitHubOAuthFlow") as mock_oauth_flow,
        patch("gitbrag.services.github.auth.GitHubAPIClient") as mock_client_class,
    ):
        # Mock OAuth flow
        mock_flow_instance = AsyncMock()
        mock_flow_instance.authenticate = AsyncMock(return_value="oauth_access_token")
        mock_oauth_flow.return_value = mock_flow_instance

        # Mock GitHubAPIClient
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        client = GitHubClient(settings=github_app_settings)
        github = await client.get_authenticated_client()

        assert github is not None
        mock_oauth_flow.assert_called_once()
        mock_flow_instance.authenticate.assert_called_once()


@pytest.mark.asyncio
async def test_authentication_missing_token() -> None:
    """Test authentication fails without token in PAT mode."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.PAT,
        github_token=SecretStr("dummy"),  # Will be set to None below
    )
    # Bypass validator for testing
    settings.github_token = None

    client = GitHubClient(settings=settings)

    with pytest.raises(ValueError, match="GitHub PAT token not configured"):
        await client.get_authenticated_client()


@pytest.mark.asyncio
async def test_authentication_missing_github_app_credentials() -> None:
    """Test authentication fails without GitHub App credentials."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.GITHUB_APP,
        github_app_client_id="test",
        github_app_client_secret=SecretStr("test"),
    )
    # Bypass validator for testing
    settings.github_app_client_id = None

    client = GitHubClient(settings=settings)

    with pytest.raises(ValueError, match="GitHub App credentials not configured"):
        await client.get_authenticated_client()


# Note: Client caching test removed - GitHubAPIClient is lightweight and doesn't need caching
# Note: Rate limit checking is now handled within GitHubAPIClient, not in the auth wrapper
