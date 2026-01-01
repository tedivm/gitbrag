"""Unit tests for background task management."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import BackgroundTasks

from gitbrag.services.background_tasks import (
    generate_params_hash,
    generate_report_background,
    schedule_report_generation,
)
from gitbrag.services.cache import configure_caches, get_cache


@pytest_asyncio.fixture(autouse=True)
async def setup_cache():
    """Set up cache for all tests."""
    configure_caches()
    cache = get_cache("persistent")
    await cache.clear()
    yield
    await cache.clear()


def test_generate_params_hash_consistency():
    """Test that generate_params_hash creates consistent hashes."""
    hash1 = generate_params_hash(show_star_increase=True)
    hash2 = generate_params_hash(show_star_increase=True)
    assert hash1 == hash2

    # Different parameters should produce different hashes
    hash3 = generate_params_hash(show_star_increase=False)
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_schedule_report_generation_registers_task():
    """Test that schedule_report_generation registers task and schedules background work."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "test_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with valid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

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
async def test_schedule_report_generation_returns_false_for_duplicate():
    """Test that schedule_report_generation returns False for duplicate tasks."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "test_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with valid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Schedule first task
        result1 = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )
        assert result1 is True

        # Try to schedule duplicate - should fail
        result2 = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )
        assert result2 is False


@pytest.mark.asyncio
async def test_schedule_report_generation_respects_per_user_limits():
    """Test that schedule_report_generation respects per-reported-user limits."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    token = "test_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with valid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Schedule first task for this reported user
        result1 = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period="1_year",
            params_hash="abc123",
            token=token,
        )
        assert result1 is True

        # Try to schedule second task for same reported user (different period)
        # Should fail due to per-user rate limit
        result2 = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period="2_years",
            params_hash="def456",
            token=token,
        )
        assert result2 is False


@pytest.mark.asyncio
async def test_schedule_report_allows_concurrent_tasks_for_different_users():
    """Test that schedule_report_generation allows concurrent tasks for different reported users."""
    background_tasks1 = BackgroundTasks()
    background_tasks2 = BackgroundTasks()
    token = "test_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock GitHubAPIClient with valid token validation
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(return_value=True)
        mock_client_class.return_value = mock_client_instance

        # Schedule task for user1
        result1 = await schedule_report_generation(
            background_tasks=background_tasks1,
            username="user1",
            period="1_year",
            params_hash="abc123",
            token=token,
        )
        assert result1 is True

        # Schedule task for user2 - should succeed
        result2 = await schedule_report_generation(
            background_tasks=background_tasks2,
            username="user2",
            period="1_year",
            params_hash="abc123",
            token=token,
        )
        assert result2 is True


@pytest.mark.asyncio
async def test_generate_report_background_updates_cache():
    """Test that generate_report_background updates cache on success."""
    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "test_token"  # Provide a token so it doesn't exit early

    # Mock the generate_report_data function to avoid actual GitHub API calls
    mock_report_data = {
        "username": username,
        "total_prs": 10,
        "merged_count": 8,
        "open_count": 1,
        "closed_count": 1,
        "repo_count": 3,
        "repositories": {},
        "prs": [],
    }

    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_report_data

        # Run background task
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

        # Verify cache was updated
        cache = get_cache("persistent")
        # The function recalculates params_hash internally, so we need to do the same
        import hashlib
        import json

        params = {"show_star_increase": True}
        actual_params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        cache_key = f"report:{username}:{period}:{actual_params_hash}"
        cached_data = await cache.get(cache_key)

        assert cached_data is not None
        assert cached_data["username"] == username
        assert cached_data["total_prs"] == 10


@pytest.mark.asyncio
async def test_generate_report_background_cleans_up_on_failure():
    """Test that generate_report_background cleans up task on failure."""
    from gitbrag.services.task_tracking import is_task_active, start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = None

    # Register task first
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)
    assert await is_task_active(task_id) is True

    # Mock generate_report_data to raise an exception
    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("Test error")

        # Run background task - should not raise
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Task should be cleaned up even after failure
    assert await is_task_active(task_id) is False


@pytest.mark.asyncio
async def test_generate_report_background_handles_github_api_errors():
    """Test that generate_report_background handles GitHub API errors gracefully."""
    from gitbrag.services.task_tracking import start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = None

    # Register task
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)

    # Mock GitHub API error
    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("GitHub API error")

        # Should not raise exception
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Cache should remain empty (no update on error)
    cache = get_cache("persistent")
    cache_key = f"report:{username}:{period}:{params_hash}"
    cached_data = await cache.get(cache_key)
    assert cached_data is None


@pytest.mark.asyncio
async def test_schedule_report_with_invalid_token():
    """Test that schedule_report_generation returns False with invalid token."""
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

        result = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

        # Should return False (not scheduled)
        assert result is False
        # No background tasks should be scheduled
        assert len(background_tasks.tasks) == 0


@pytest.mark.asyncio
async def test_schedule_report_with_valid_token():
    """Test that schedule_report_generation succeeds with valid token."""
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
async def test_schedule_report_with_validation_error():
    """Test that schedule_report_generation returns False when validation raises exception."""
    background_tasks = BackgroundTasks()
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "test_token"

    with patch("gitbrag.services.background_tasks.GitHubAPIClient") as mock_client_class:
        # Mock validation raising an exception
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.validate_token = AsyncMock(side_effect=Exception("Network error"))
        mock_client_class.return_value = mock_client_instance

        result = await schedule_report_generation(
            background_tasks=background_tasks,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

        # Should return False (not scheduled)
        assert result is False
        # No background tasks should be scheduled
        assert len(background_tasks.tasks) == 0


@pytest.mark.asyncio
async def test_generate_report_background_aborts_on_401_error():
    """Test that generate_report_background aborts early on 401 authentication error."""
    import httpx

    from gitbrag.services.task_tracking import is_task_active, start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "expired_token"

    # Register task
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)

    # Mock generate_report_data to raise 401 error
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.headers = {}

    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = httpx.HTTPStatusError("Unauthorized", request=AsyncMock(), response=mock_response)

        # Should not raise exception
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Task should be cleaned up
    assert await is_task_active(task_id) is False


@pytest.mark.asyncio
async def test_generate_report_background_aborts_on_403_auth_error():
    """Test that generate_report_background aborts on 403 (non-rate-limit) authentication error."""
    import httpx

    from gitbrag.services.task_tracking import is_task_active, start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "forbidden_token"

    # Register task
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)

    # Mock generate_report_data to raise 403 error (not rate limit)
    mock_response = AsyncMock()
    mock_response.status_code = 403
    mock_response.headers = {"X-RateLimit-Remaining": "100"}  # Not a rate limit

    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = httpx.HTTPStatusError("Forbidden", request=AsyncMock(), response=mock_response)

        # Should not raise exception
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Task should be cleaned up
    assert await is_task_active(task_id) is False


@pytest.mark.asyncio
async def test_generate_report_background_continues_on_rate_limit():
    """Test that generate_report_background handles rate limit errors normally (not as auth error)."""
    import httpx

    from gitbrag.services.task_tracking import is_task_active, start_task

    task_id = "testuser:1_year:abc123"
    username = "testuser"
    period = "1_year"
    params_hash = "abc123"
    token = "valid_token"

    # Register task
    metadata = {
        "username": username,
        "period": period,
        "params_hash": params_hash,
        "started_at": 1234567890,
    }
    await start_task(task_id, metadata)

    # Mock generate_report_data to raise 403 rate limit error
    mock_response = AsyncMock()
    mock_response.status_code = 403
    mock_response.headers = {"X-RateLimit-Remaining": "0"}  # This is a rate limit

    with patch("gitbrag.services.background_tasks.generate_report_data", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = httpx.HTTPStatusError(
            "Rate limit exceeded", request=AsyncMock(), response=mock_response
        )

        # Should not raise exception
        await generate_report_background(
            task_id=task_id,
            username=username,
            period=period,
            params_hash=params_hash,
            token=token,
        )

    # Task should still be cleaned up (in finally block)
    assert await is_task_active(task_id) is False
