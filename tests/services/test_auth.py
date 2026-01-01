"""Tests for authentication dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from gitbrag.services.auth import get_authenticated_github_client


@pytest.fixture
def mock_request_with_session():
    """Create a mock request with session."""
    request = MagicMock()
    request.session = {"authenticated": True}
    request.url = "http://testserver/profile"
    return request


@pytest.fixture
def mock_request_unauthenticated():
    """Create a mock request without authentication."""
    request = MagicMock()
    request.session = {}
    request.url = "http://testserver/profile"
    return request


@pytest.mark.asyncio
async def test_get_authenticated_client_with_valid_token(mock_request_with_session):
    """Test get_authenticated_github_client with valid token."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("valid_token")

        # Mock GitHubAPIClient and its validate_token method
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Call function
        result = await get_authenticated_github_client(mock_request_with_session)

        # Assertions
        assert result == mock_client_instance
        mock_is_auth.assert_called_once_with(mock_request_with_session)
        mock_client_instance.validate_token.assert_called_once()


@pytest.mark.asyncio
async def test_get_authenticated_client_with_invalid_token(mock_request_with_session):
    """Test get_authenticated_github_client with invalid token raises 401."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
        patch("gitbrag.services.auth.invalidate_session") as mock_invalidate,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("invalid_token")

        # Mock GitHubAPIClient - validate_token returns False
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client_instance

        # Call function and expect 401
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_github_client(mock_request_with_session)

        # Assertions
        assert exc_info.value.status_code == 401
        assert "session has expired" in exc_info.value.detail.lower()
        mock_invalidate.assert_called_once_with(mock_request_with_session, reason="token validation failed")


@pytest.mark.asyncio
async def test_get_authenticated_client_clears_session_on_failure(mock_request_with_session):
    """Test that session is cleared when token validation fails."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
        patch("gitbrag.services.auth.invalidate_session") as mock_invalidate,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("expired_token")

        # Mock GitHubAPIClient - validate_token returns False
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client_instance

        # Call function and expect HTTPException
        with pytest.raises(HTTPException):
            await get_authenticated_github_client(mock_request_with_session)

        # Verify invalidate_session was called
        mock_invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_get_authenticated_client_not_authenticated(mock_request_unauthenticated):
    """Test get_authenticated_github_client raises 401 when not authenticated."""
    with patch("gitbrag.services.auth.is_authenticated") as mock_is_auth:
        mock_is_auth.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_github_client(mock_request_unauthenticated)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_authenticated_client_stores_redirect_url(mock_request_unauthenticated):
    """Test that original URL is stored for post-login redirect."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.set_session_data") as mock_set_session,
    ):
        mock_is_auth.return_value = False

        try:
            await get_authenticated_github_client(mock_request_unauthenticated)
        except HTTPException:
            pass

        # Verify redirect URL was stored
        mock_set_session.assert_called_once()
        call_args = mock_set_session.call_args
        assert call_args[0][1] == "redirect_after_login"
        assert "http://testserver/profile" in call_args[0][2]


@pytest.mark.asyncio
async def test_get_authenticated_client_with_none_token(mock_request_with_session):
    """Test get_authenticated_github_client raises 401 when token is None."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
    ):
        mock_is_auth.return_value = True
        mock_get_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_github_client(mock_request_with_session)

        assert exc_info.value.status_code == 401
        assert "Invalid session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_authenticated_client_validation_network_error(mock_request_with_session):
    """Test handling of network errors during token validation."""
    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("valid_token")

        # Mock GitHubAPIClient - validate_token raises network error
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(side_effect=httpx.TimeoutException("Network timeout"))
        mock_client_class.return_value = mock_client_instance

        # Call function and expect 500 (wrapped as internal error)
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_github_client(mock_request_with_session)

        assert exc_info.value.status_code == 500
