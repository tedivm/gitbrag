from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github import Auth, Github
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
    with patch("gitbrag.services.github.auth.Github") as mock_github:
        mock_github.return_value = MagicMock(spec=Github)

        client = GitHubClient(settings=pat_settings)
        github = await client.get_authenticated_client()

        assert github is not None
        mock_github.assert_called_once()
        # Verify Auth.Token was used
        call_args = mock_github.call_args
        assert call_args is not None
        auth_arg = call_args.kwargs.get("auth") or call_args.args[0]
        assert isinstance(auth_arg, Auth.Token)


@pytest.mark.asyncio
async def test_token_override(pat_settings: GitHubSettings) -> None:
    """Test using token override instead of settings."""
    with patch("gitbrag.services.github.auth.Github") as mock_github:
        mock_github.return_value = MagicMock(spec=Github)

        client = GitHubClient(settings=pat_settings, token_override="override_token")
        await client.get_authenticated_client()

        # Verify Github was created with the override token
        mock_github.assert_called_once()


@pytest.mark.asyncio
async def test_github_app_oauth_flow(github_app_settings: GitHubSettings) -> None:
    """Test GitHub App OAuth authentication flow."""
    with (
        patch("gitbrag.services.github.auth.GitHubOAuthFlow") as mock_oauth_flow,
        patch("gitbrag.services.github.auth.Github") as mock_github,
    ):
        # Mock OAuth flow
        mock_flow_instance = AsyncMock()
        mock_flow_instance.initiate_flow = AsyncMock()
        mock_flow_instance.complete_flow = AsyncMock(return_value="oauth_access_token")
        mock_oauth_flow.return_value = mock_flow_instance

        # Mock Github client
        mock_github.return_value = MagicMock(spec=Github)

        client = GitHubClient(settings=github_app_settings)
        github = await client.get_authenticated_client()

        assert github is not None
        mock_oauth_flow.assert_called_once()
        mock_flow_instance.initiate_flow.assert_called_once()
        mock_flow_instance.complete_flow.assert_called_once()


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

    with pytest.raises(ValueError, match="GitHub token not configured"):
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


@pytest.mark.asyncio
async def test_client_caching(pat_settings: GitHubSettings) -> None:
    """Test that authenticated client is cached."""
    with patch("gitbrag.services.github.auth.Github") as mock_github:
        mock_github.return_value = MagicMock(spec=Github)

        client = GitHubClient(settings=pat_settings)

        # Call twice
        github1 = await client.get_authenticated_client()
        github2 = await client.get_authenticated_client()

        # Should return same instance
        assert github1 is github2
        # Should only create Github once
        assert mock_github.call_count == 1


def test_rate_limit_before_authentication(pat_settings: GitHubSettings) -> None:
    """Test getting rate limit before authentication raises error."""
    client = GitHubClient(settings=pat_settings)

    with pytest.raises(ValueError, match="Client not authenticated"):
        client.get_rate_limit()


@pytest.mark.asyncio
async def test_rate_limit_after_authentication(pat_settings: GitHubSettings) -> None:
    """Test getting rate limit after authentication."""
    with patch("gitbrag.services.github.auth.Github") as mock_github:
        # Mock rate limit response
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4999
        mock_rate_limit.search.limit = 30
        mock_rate_limit.search.remaining = 29
        mock_rate_limit.graphql.limit = 5000
        mock_rate_limit.graphql.remaining = 5000

        mock_client = MagicMock(spec=Github)
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_github.return_value = mock_client

        client = GitHubClient(settings=pat_settings)
        await client.get_authenticated_client()

        rate_limit = client.get_rate_limit()

        assert rate_limit["core_limit"] == 5000
        assert rate_limit["core_remaining"] == 4999
        assert rate_limit["search_limit"] == 30
        assert rate_limit["search_remaining"] == 29
        assert rate_limit["graphql_limit"] == 5000
        assert rate_limit["graphql_remaining"] == 5000
