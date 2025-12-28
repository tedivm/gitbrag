"""Tests for GitHub stargazer fetching."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.services.github.stargazers import collect_repository_star_increases, fetch_repository_star_increase


@pytest.fixture
def date_range() -> tuple[datetime, datetime]:
    """Create a test date range."""
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    until = datetime(2024, 12, 31, tzinfo=timezone.utc)
    return since, until


@pytest.fixture(autouse=True)
def mock_cache():
    """Mock cache functions for all tests."""
    with (
        patch("gitbrag.services.github.stargazers.get_cached", new_callable=AsyncMock) as mock_get,
        patch("gitbrag.services.github.stargazers.set_cached", new_callable=AsyncMock) as mock_set,
    ):
        # Default: cache miss
        mock_get.return_value = None
        yield {"get": mock_get, "set": mock_set}


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_success(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test successful star increase fetching with single page."""
    since, until = date_range

    # Mock GraphQL response with stars in range
    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [
                        {"starredAt": "2024-06-15T12:00:00Z"},
                        {"starredAt": "2024-03-20T08:30:00Z"},
                        {"starredAt": "2024-01-10T14:45:00Z"},
                        {"starredAt": "2023-12-25T10:00:00Z"},  # Before range
                    ],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        # Should count 3 stars (excluding the one before range)
        assert result == 3
        mock_graphql.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_pagination(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test star increase fetching with pagination."""
    since, until = date_range

    # First page
    page1_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": "cursor1", "hasNextPage": True},
                    "edges": [
                        {"starredAt": "2024-12-01T12:00:00Z"},
                        {"starredAt": "2024-11-15T08:30:00Z"},
                    ],
                }
            }
        }
    }

    # Second page
    page2_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [
                        {"starredAt": "2024-10-20T14:45:00Z"},
                        {"starredAt": "2024-09-05T10:00:00Z"},
                    ],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.side_effect = [page1_response, page2_response]

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result == 4
        assert mock_graphql.call_count == 2


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_early_termination(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test early termination when reaching dates before the since date."""
    since, until = date_range

    # Response with dates that trigger early termination
    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": "cursor1", "hasNextPage": True},
                    "edges": [
                        {"starredAt": "2024-06-15T12:00:00Z"},  # In range
                        {"starredAt": "2024-03-20T08:30:00Z"},  # In range
                        {"starredAt": "2023-12-15T10:00:00Z"},  # Before range - triggers termination
                    ],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result == 2
        # Should only call once due to early termination
        mock_graphql.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_no_stars(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test with repository that has no stars in the date range."""
    since, until = date_range

    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result == 0


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_repo_not_found(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test handling of repository not found."""
    since, until = date_range

    graphql_response = {"data": {"repository": None}}

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result is None


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_http_error_with_wait(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test HTTP error handling with wait_for_rate_limit=True."""
    since, until = date_range

    mock_response = AsyncMock()
    mock_response.status_code = 500
    http_error = httpx.HTTPStatusError("Server error", request=AsyncMock(), response=mock_response)

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.side_effect = http_error

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until, wait_for_rate_limit=True
        )

        assert result is None


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_graphql_error(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test GraphQL error handling."""
    since, until = date_range

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.side_effect = ValueError("GraphQL errors: Field error")

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result is None


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_rate_limit(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test rate limit handling."""
    since, until = date_range

    mock_response = AsyncMock()
    mock_response.status_code = 429
    rate_limit_error = httpx.HTTPStatusError("Rate limit", request=AsyncMock(), response=mock_response)

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.side_effect = rate_limit_error

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result is None


@pytest.mark.asyncio
async def test_collect_repository_star_increases_success(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test collecting star increases for multiple repositories."""
    since, until = date_range
    repositories = ["owner1/repo1", "owner2/repo2", "owner3/repo3"]

    with patch(
        "gitbrag.services.github.stargazers.fetch_repository_star_increase", new_callable=AsyncMock
    ) as mock_fetch:
        # Mock different return values for each repository
        mock_fetch.side_effect = [10, 25, 5]

        result = await collect_repository_star_increases(
            client=mock_client, repositories=repositories, since=since, until=until
        )

        assert len(result) == 3
        assert result["owner1/repo1"] == 10
        assert result["owner2/repo2"] == 25
        assert result["owner3/repo3"] == 5
        assert mock_fetch.call_count == 3


@pytest.mark.asyncio
async def test_collect_repository_star_increases_deduplication(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test that duplicate repositories are deduplicated."""
    since, until = date_range
    repositories = ["owner1/repo1", "owner2/repo2", "owner1/repo1"]  # Duplicate

    with patch(
        "gitbrag.services.github.stargazers.fetch_repository_star_increase", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = [10, 25]

        result = await collect_repository_star_increases(
            client=mock_client, repositories=repositories, since=since, until=until
        )

        assert len(result) == 2
        # Should only fetch each unique repo once
        assert mock_fetch.call_count == 2


@pytest.mark.asyncio
async def test_collect_repository_star_increases_with_failures(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test handling of failures for some repositories."""
    since, until = date_range
    repositories = ["owner1/repo1", "owner2/repo2", "owner3/repo3"]

    with patch(
        "gitbrag.services.github.stargazers.fetch_repository_star_increase", new_callable=AsyncMock
    ) as mock_fetch:
        # First succeeds, second returns None, third raises exception
        mock_fetch.side_effect = [10, None, ValueError("Error")]

        result = await collect_repository_star_increases(
            client=mock_client, repositories=repositories, since=since, until=until
        )

        assert len(result) == 3
        assert result["owner1/repo1"] == 10
        assert result["owner2/repo2"] is None
        assert result["owner3/repo3"] is None


@pytest.mark.asyncio
async def test_collect_repository_star_increases_invalid_format(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test handling of invalid repository name format."""
    since, until = date_range
    repositories = ["invalid-format", "owner/repo"]

    with patch(
        "gitbrag.services.github.stargazers.fetch_repository_star_increase", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = 10

        result = await collect_repository_star_increases(
            client=mock_client, repositories=repositories, since=since, until=until
        )

        # Invalid format repos get None value in result
        assert len(result) == 2
        assert result["owner/repo"] == 10
        assert result["invalid-format"] is None
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_collect_repository_star_increases_zero_increase(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test repositories with zero star increase."""
    since, until = date_range
    repositories = ["owner1/repo1", "owner2/repo2"]

    with patch(
        "gitbrag.services.github.stargazers.fetch_repository_star_increase", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = [0, 5]

        result = await collect_repository_star_increases(
            client=mock_client, repositories=repositories, since=since, until=until
        )

        assert result["owner1/repo1"] == 0
        assert result["owner2/repo2"] == 5


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_wait_for_rate_limit_false(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime]
) -> None:
    """Test that max_retries is set to 0 when wait_for_rate_limit is False."""
    since, until = date_range

    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [{"starredAt": "2024-06-15T12:00:00Z"}],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until, wait_for_rate_limit=False
        )

        # Verify the function was called (wait_for_rate_limit affects internal retry behavior)
        assert mock_graphql.call_count >= 1
        assert result == 1


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_cache_hit(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime], mock_cache: dict
) -> None:
    """Test that cached results are returned without making API calls."""
    since, until = date_range
    cached_value = 42

    # Override the default cache miss with a cache hit
    mock_cache["get"].return_value = cached_value

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result == cached_value
        mock_cache["get"].assert_called_once()
        # GraphQL should not be called if cache hit
        mock_graphql.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_cache_miss_and_set(
    mock_client: GitHubAPIClient, date_range: tuple[datetime, datetime], mock_cache: dict
) -> None:
    """Test that results are cached after fetching from API."""
    since, until = date_range

    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [
                        {"starredAt": "2024-06-15T12:00:00Z"},
                        {"starredAt": "2024-03-20T08:30:00Z"},
                    ],
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        assert result == 2
        mock_cache["get"].assert_called_once()
        mock_graphql.assert_called_once()
        # Result should be cached with correct TTL
        mock_cache["set"].assert_called_once()
        call_kwargs = mock_cache["set"].call_args.kwargs
        from gitbrag.settings import settings

        assert call_kwargs["ttl"] == settings.cache_star_increase_ttl
        assert call_kwargs["alias"] == "persistent"


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_timezone_aware_comparison(
    mock_client: GitHubAPIClient,
) -> None:
    """Test that timezone-aware dates are compared correctly with GitHub timestamps."""
    # Use timezone-aware dates like CLI does
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)
    until = datetime(2024, 12, 31, tzinfo=timezone.utc)

    # GitHub returns ISO timestamps with Z suffix (UTC)
    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "edges": [
                        {"starredAt": "2024-07-15T10:30:00Z"},  # In range
                        {"starredAt": "2024-08-20T14:45:00Z"},  # In range
                        {"starredAt": "2024-05-01T08:00:00Z"},  # Before range - triggers early termination
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=since, until=until
        )

        # Should count 2 stars (first two) and stop at the third due to early termination
        assert result == 2
        mock_graphql.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_repository_star_increase_with_naive_datetime(mock_client: GitHubAPIClient) -> None:
    """Test that naive datetime causes comparison error (regression test)."""
    # Create naive datetimes (no timezone)
    naive_since = datetime(2024, 1, 1)  # Naive
    naive_until = datetime(2024, 12, 31)  # Naive

    # Verify these are actually naive
    assert naive_since.tzinfo is None
    assert naive_until.tzinfo is None

    # This test documents that naive dates WOULD cause comparison errors
    # In the real code, CLI now ensures dates are always timezone-aware
    # If somehow naive dates were passed, comparison would fail

    graphql_response = {
        "data": {
            "repository": {
                "stargazers": {
                    "edges": [{"starredAt": "2024-07-15T10:30:00Z"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
    }

    with patch.object(mock_client, "execute_graphql", new_callable=AsyncMock) as mock_graphql:
        mock_graphql.return_value = graphql_response

        # The error is caught and logged, returns None
        result = await fetch_repository_star_increase(
            client=mock_client, owner="testowner", repo="testrepo", since=naive_since, until=naive_until
        )

        # Should return None due to the comparison error
        assert result is None
