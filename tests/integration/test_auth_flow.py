"""Integration tests for authentication flow with token validation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from gitbrag.services.background_tasks import schedule_report_generation


@pytest.mark.asyncio
async def test_expired_token_redirects_to_login():
    """Test end-to-end flow: expired token triggers session invalidation and 401 response."""
    from fastapi import HTTPException
    from pydantic import SecretStr

    from gitbrag.services.auth import get_authenticated_github_client

    # Create mock request with session
    mock_request = MagicMock()
    mock_request.session = {"authenticated": True}
    mock_request.url = "http://testserver/profile"

    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
        patch("gitbrag.services.auth.invalidate_session") as mock_invalidate,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("expired_token")

        # Mock GitHubAPIClient with failed validation
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client_instance

        # Call authentication and expect 401
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_github_client(mock_request)

        # Verify 401 response
        assert exc_info.value.status_code == 401
        assert "session has expired" in exc_info.value.detail.lower()

        # Verify session was invalidated
        mock_invalidate.assert_called_once_with(mock_request, reason="token validation failed")


@pytest.mark.asyncio
async def test_background_job_rejected_with_invalid_token():
    """Test end-to-end flow: background job scheduling is rejected with invalid token."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "invalid_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with invalid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_client_instance

        # Try to schedule background job
        result = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

        # Should be rejected
        assert result is False
        # No background tasks should be scheduled
        assert len(background_tasks.tasks) == 0


@pytest.mark.asyncio
async def test_valid_token_flow_succeeds():
    """Test end-to-end flow: valid token allows normal operation."""
    from pydantic import SecretStr

    from gitbrag.services.auth import get_authenticated_github_client

    # Create mock request with session
    mock_request = MagicMock()
    mock_request.session = {"authenticated": True}
    mock_request.url = "http://testserver/profile"

    with (
        patch("gitbrag.services.auth.is_authenticated") as mock_is_auth,
        patch("gitbrag.services.auth.get_decrypted_token") as mock_get_token,
        patch("gitbrag.services.auth.GitHubAPIClient") as mock_client_class,
    ):
        # Setup mocks
        mock_is_auth.return_value = True
        mock_get_token.return_value = SecretStr("valid_token")

        # Mock GitHubAPIClient with successful validation
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Call authentication
        result = await get_authenticated_github_client(mock_request)

        # Should succeed and return client
        assert result == mock_client_instance
        mock_client_instance.validate_token.assert_called_once()


@pytest.mark.asyncio
async def test_background_job_with_valid_token_succeeds():
    """Test end-to-end flow: background job scheduling succeeds with valid token."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "valid_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with valid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Schedule background job
        result = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

        # Should succeed
        assert result is True
        # Should have one background task scheduled
        assert len(background_tasks.tasks) == 1


@pytest.mark.asyncio
async def test_background_job_aborts_on_expired_token_during_execution():
    """Test end-to-end flow: background job aborts when token expires during execution."""
    import httpx
    from gitbrag.services.task_tracking import is_task_active, start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "expired_during_execution"

    # Register task
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)

    # Mock generate_report_data to raise 401 error (token expired during execution)
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {}

    from gitbrag.services.background_tasks import generate_report_background

    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = httpx.HTTPStatusError("Unauthorized", request=AsyncMock(), response=mock_response)

        # Execute background job
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Task should be cleaned up (aborted early)
    assert await is_task_active(task_id) is False
