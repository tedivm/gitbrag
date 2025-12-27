from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gitbrag.services.github.pullrequests import PullRequestCollector


@pytest.fixture
def mock_github_client() -> AsyncMock:
    """Create a mock GitHub client."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_collect_user_prs_success(
    mock_github_client: AsyncMock,
) -> None:
    """Test successful PR collection."""
    # Mock search_all_issues to return a list of dict items
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Test PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].title == "Test PR"
    assert prs[0].repository == "owner/repo"
    assert prs[0].state == "closed"
    assert prs[0].organization == "owner"
    assert prs[0].merged_at is not None


@pytest.mark.asyncio
async def test_collect_user_prs_with_date_filter(
    mock_github_client: AsyncMock,
) -> None:
    """Test PR collection with date filtering."""
    mock_github_client.search_all_issues.return_value = []

    collector = PullRequestCollector(mock_github_client)
    since = datetime(2024, 1, 1)
    until = datetime(2024, 12, 31)

    await collector.collect_user_prs(
        username="testuser",
        since=since,
        until=until,
    )

    # Verify search query includes date filters with range syntax
    call_args = mock_github_client.search_all_issues.call_args
    query = call_args.kwargs["query"]
    assert "updated:2024-01-01..2024-12-31" in query


@pytest.mark.asyncio
async def test_collect_user_prs_private_excluded_by_default(
    mock_github_client: AsyncMock,
) -> None:
    """Test that private repository PRs are excluded by default."""
    # With httpx implementation, GitHub API handles private filtering
    # Mock returns only public PRs when include_private=False
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Public PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser", include_private=False)

    # Should only get public PR
    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].repository == "owner/repo"


@pytest.mark.asyncio
async def test_collect_user_prs_include_private(
    mock_github_client: AsyncMock,
) -> None:
    """Test including private repository PRs."""
    # Mock returns both public and private PRs when include_private=True
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Public PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        },
        {
            "number": 456,
            "title": "Private PR",
            "state": "closed",
            "created_at": "2024-02-01T12:00:00Z",
            "closed_at": "2024-02-02T12:00:00Z",
            "html_url": "https://github.com/owner/private-repo/pull/456",
            "repository_url": "https://api.github.com/repos/owner/private-repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-02-02T12:00:00Z"},
        },
    ]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser", include_private=True)

    # Should get both PRs
    assert len(prs) == 2
    assert prs[0].number == 123
    assert prs[1].number == 456


@pytest.mark.asyncio
async def test_collect_user_prs_user_not_found(mock_github_client: AsyncMock) -> None:
    """Test error handling when user not found."""
    # Mock HTTP 422 error for invalid username
    response = MagicMock()
    response.status_code = 422
    mock_github_client.search_all_issues.side_effect = httpx.HTTPStatusError(
        "422 Unprocessable Entity",
        request=MagicMock(),
        response=response,
    )

    collector = PullRequestCollector(mock_github_client)

    # httpx errors propagate as empty list in current implementation
    prs = await collector.collect_user_prs(username="nonexistent")
    assert prs == []


@pytest.mark.asyncio
async def test_collect_user_prs_permission_denied(mock_github_client: AsyncMock) -> None:
    """Test error handling for permission errors."""
    # Mock HTTP 403 error for permission denied
    response = MagicMock()
    response.status_code = 403
    mock_github_client.search_all_issues.side_effect = httpx.HTTPStatusError(
        "403 Forbidden",
        request=MagicMock(),
        response=response,
    )

    collector = PullRequestCollector(mock_github_client)

    # 403 errors should raise
    with pytest.raises(httpx.HTTPStatusError):
        await collector.collect_user_prs(username="testuser")


@pytest.mark.asyncio
async def test_collect_user_prs_merged_pr(
    mock_github_client: AsyncMock,
) -> None:
    """Test collecting merged pull request."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 789,
            "title": "Merged PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/789",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert len(prs) == 1
    assert prs[0].state == "closed"
    assert prs[0].merged_at is not None
    assert prs[0].closed_at is not None


@pytest.mark.asyncio
async def test_collect_user_prs_empty_results(
    mock_github_client: AsyncMock,
) -> None:
    """Test handling empty search results."""
    mock_github_client.search_all_issues.return_value = []

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="nonexistent")

    assert len(prs) == 0


@pytest.mark.asyncio
async def test_collect_user_prs_organization_extraction(
    mock_github_client: AsyncMock,
) -> None:
    """Test extraction of organization from repository full name."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 100,
            "title": "Test",
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": None,
            "html_url": "https://github.com/my-org/my-repo/pull/100",
            "repository_url": "https://api.github.com/repos/my-org/my-repo",
            "user": {"login": "testuser"},
            "pull_request": {},
        }
    ]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert prs[0].organization == "my-org"


@pytest.mark.asyncio
async def test_collect_user_prs_with_star_increase(
    mock_github_client: AsyncMock,
) -> None:
    """Test PR collection with star increase enabled."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Test PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    with patch(
        "gitbrag.services.github.pullrequests.collect_repository_star_increases", new_callable=AsyncMock
    ) as mock_collect:
        mock_collect.return_value = {"owner/repo": 42}

        collector = PullRequestCollector(mock_github_client)
        since = datetime(2024, 1, 1)
        until = datetime(2024, 12, 31)

        prs = await collector.collect_user_prs(
            username="testuser",
            since=since,
            until=until,
            include_star_increase=True,
        )

        assert len(prs) == 1
        assert prs[0].star_increase == 42
        mock_collect.assert_called_once()


@pytest.mark.asyncio
async def test_collect_user_prs_without_star_increase(
    mock_github_client: AsyncMock,
) -> None:
    """Test PR collection with star increase disabled."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Test PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    with patch(
        "gitbrag.services.github.pullrequests.collect_repository_star_increases", new_callable=AsyncMock
    ) as mock_collect:
        collector = PullRequestCollector(mock_github_client)
        since = datetime(2024, 1, 1)
        until = datetime(2024, 12, 31)

        prs = await collector.collect_user_prs(
            username="testuser",
            since=since,
            until=until,
            include_star_increase=False,
        )

        assert len(prs) == 1
        assert prs[0].star_increase is None
        # Shouldn't call star collection when disabled
        mock_collect.assert_not_called()


@pytest.mark.asyncio
async def test_collect_user_prs_star_increase_deduplicates_repos(
    mock_github_client: AsyncMock,
) -> None:
    """Test that duplicate repositories are deduplicated when collecting star increases."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Test PR 1",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        },
        {
            "number": 456,
            "title": "Test PR 2",
            "state": "closed",
            "created_at": "2024-02-01T12:00:00Z",
            "closed_at": "2024-02-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/456",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-02-02T12:00:00Z"},
        },
    ]

    with patch(
        "gitbrag.services.github.pullrequests.collect_repository_star_increases", new_callable=AsyncMock
    ) as mock_collect:
        mock_collect.return_value = {"owner/repo": 42}

        collector = PullRequestCollector(mock_github_client)
        since = datetime(2024, 1, 1)
        until = datetime(2024, 12, 31)

        prs = await collector.collect_user_prs(
            username="testuser",
            since=since,
            until=until,
            include_star_increase=True,
        )

        assert len(prs) == 2
        # Should call with unique repositories only
        call_args = mock_collect.call_args
        repositories = call_args.kwargs["repositories"]
        assert len(repositories) == 1
        assert "owner/repo" in repositories


@pytest.mark.asyncio
async def test_collect_user_prs_star_increase_without_dates(
    mock_github_client: AsyncMock,
) -> None:
    """Test that star increase is not collected without since/until dates."""
    mock_github_client.search_all_issues.return_value = [
        {
            "number": 123,
            "title": "Test PR",
            "state": "closed",
            "created_at": "2024-01-01T12:00:00Z",
            "closed_at": "2024-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/123",
            "repository_url": "https://api.github.com/repos/owner/repo",
            "user": {"login": "testuser"},
            "pull_request": {"merged_at": "2024-01-02T12:00:00Z"},
        }
    ]

    with patch(
        "gitbrag.services.github.pullrequests.collect_repository_star_increases", new_callable=AsyncMock
    ) as mock_collect:
        collector = PullRequestCollector(mock_github_client)

        prs = await collector.collect_user_prs(
            username="testuser",
            include_star_increase=True,  # Enabled but no dates
        )

        assert len(prs) == 1
        assert prs[0].star_increase is None
        # Shouldn't call star collection without date range
        mock_collect.assert_not_called()
