from datetime import datetime
from unittest.mock import MagicMock

import pytest
from github import GithubException

from gitbrag.services.github.pullrequests import PullRequestCollector


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mock GitHub client."""
    return MagicMock()


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock GitHub user."""
    user = MagicMock()
    user.login = "testuser"
    return user


@pytest.fixture
def mock_pr() -> MagicMock:
    """Create a mock pull request."""
    pr = MagicMock()
    pr.number = 123
    pr.title = "Test PR"
    pr.state = "open"
    pr.html_url = "https://github.com/owner/repo/pull/123"
    pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
    pr.merged_at = None
    pr.closed_at = None
    pr.user.login = "testuser"

    # Mock repository
    pr.base.repo.full_name = "owner/repo"
    pr.base.repo.private = False

    return pr


@pytest.mark.asyncio
async def test_collect_user_prs_success(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
    mock_pr: MagicMock,
) -> None:
    """Test successful PR collection."""
    mock_github_client.get_user.return_value = mock_user

    # Mock search results
    mock_issue = MagicMock()
    mock_issue.as_pull_request.return_value = mock_pr
    mock_github_client.search_issues.return_value = [mock_issue]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].title == "Test PR"
    assert prs[0].repository == "owner/repo"
    assert prs[0].state == "open"
    assert prs[0].organization == "owner"


@pytest.mark.asyncio
async def test_collect_user_prs_with_date_filter(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
) -> None:
    """Test PR collection with date filtering."""
    mock_github_client.get_user.return_value = mock_user
    mock_github_client.search_issues.return_value = []

    collector = PullRequestCollector(mock_github_client)
    since = datetime(2024, 1, 1)
    until = datetime(2024, 12, 31)

    await collector.collect_user_prs(
        username="testuser",
        since=since,
        until=until,
    )

    # Verify search query includes date filters
    call_args = mock_github_client.search_issues.call_args
    query = call_args.kwargs["query"]
    assert "created:>=2024-01-01" in query
    assert "created:<=2024-12-31" in query


@pytest.mark.asyncio
async def test_collect_user_prs_private_excluded_by_default(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
    mock_pr: MagicMock,
) -> None:
    """Test that private repository PRs are excluded by default."""
    mock_github_client.get_user.return_value = mock_user

    # Create mock PRs - one public, one private
    public_pr = mock_pr
    private_pr = MagicMock()
    private_pr.number = 456
    private_pr.title = "Private PR"
    private_pr.base.repo.private = True
    private_pr.base.repo.full_name = "owner/private-repo"

    mock_issue1 = MagicMock()
    mock_issue1.as_pull_request.return_value = public_pr

    mock_issue2 = MagicMock()
    mock_issue2.as_pull_request.return_value = private_pr

    mock_github_client.search_issues.return_value = [mock_issue1, mock_issue2]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser", include_private=False)

    # Should only get public PR
    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].repository == "owner/repo"


@pytest.mark.asyncio
async def test_collect_user_prs_include_private(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
    mock_pr: MagicMock,
) -> None:
    """Test including private repository PRs."""
    mock_github_client.get_user.return_value = mock_user

    # Create mock PRs - one public, one private
    public_pr = mock_pr
    private_pr = MagicMock()
    private_pr.number = 456
    private_pr.title = "Private PR"
    private_pr.state = "merged"
    private_pr.html_url = "https://github.com/owner/private-repo/pull/456"
    private_pr.created_at = datetime(2024, 2, 1, 12, 0, 0)
    private_pr.merged_at = datetime(2024, 2, 2, 12, 0, 0)
    private_pr.closed_at = datetime(2024, 2, 2, 12, 0, 0)
    private_pr.user.login = "testuser"
    private_pr.base.repo.private = True
    private_pr.base.repo.full_name = "owner/private-repo"

    mock_issue1 = MagicMock()
    mock_issue1.as_pull_request.return_value = public_pr

    mock_issue2 = MagicMock()
    mock_issue2.as_pull_request.return_value = private_pr

    mock_github_client.search_issues.return_value = [mock_issue1, mock_issue2]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser", include_private=True)

    # Should get both PRs
    assert len(prs) == 2
    assert prs[0].number == 123
    assert prs[1].number == 456


@pytest.mark.asyncio
async def test_collect_user_prs_user_not_found(mock_github_client: MagicMock) -> None:
    """Test error handling when user not found."""
    mock_github_client.get_user.side_effect = GithubException(
        status=404,
        data={"message": "Not Found"},
        headers={},
    )

    collector = PullRequestCollector(mock_github_client)

    with pytest.raises(ValueError, match="User 'nonexistent' not found"):
        await collector.collect_user_prs(username="nonexistent")


@pytest.mark.asyncio
async def test_collect_user_prs_permission_denied(mock_github_client: MagicMock) -> None:
    """Test error handling for permission errors."""
    mock_github_client.get_user.side_effect = GithubException(
        status=403,
        data={"message": "Forbidden"},
        headers={},
    )

    collector = PullRequestCollector(mock_github_client)

    with pytest.raises(ValueError, match="Permission denied"):
        await collector.collect_user_prs(username="testuser")


@pytest.mark.asyncio
async def test_collect_user_prs_merged_pr(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
) -> None:
    """Test collecting merged pull request."""
    mock_github_client.get_user.return_value = mock_user

    merged_pr = MagicMock()
    merged_pr.number = 789
    merged_pr.title = "Merged PR"
    merged_pr.state = "closed"
    merged_pr.html_url = "https://github.com/owner/repo/pull/789"
    merged_pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
    merged_pr.merged_at = datetime(2024, 1, 2, 12, 0, 0)
    merged_pr.closed_at = datetime(2024, 1, 2, 12, 0, 0)
    merged_pr.user.login = "testuser"
    merged_pr.base.repo.full_name = "owner/repo"
    merged_pr.base.repo.private = False

    mock_issue = MagicMock()
    mock_issue.as_pull_request.return_value = merged_pr
    mock_github_client.search_issues.return_value = [mock_issue]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert len(prs) == 1
    assert prs[0].state == "closed"
    assert prs[0].merged_at is not None
    assert prs[0].closed_at is not None


@pytest.mark.asyncio
async def test_collect_user_prs_empty_results(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
) -> None:
    """Test handling empty search results."""
    mock_github_client.get_user.return_value = mock_user
    mock_github_client.search_issues.return_value = []

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert len(prs) == 0


@pytest.mark.asyncio
async def test_collect_user_prs_organization_extraction(
    mock_github_client: MagicMock,
    mock_user: MagicMock,
) -> None:
    """Test extraction of organization from repository full name."""
    mock_github_client.get_user.return_value = mock_user

    pr = MagicMock()
    pr.number = 100
    pr.title = "Test"
    pr.state = "open"
    pr.html_url = "https://github.com/my-org/my-repo/pull/100"
    pr.created_at = datetime(2024, 1, 1)
    pr.merged_at = None
    pr.closed_at = None
    pr.user.login = "testuser"
    pr.base.repo.full_name = "my-org/my-repo"
    pr.base.repo.private = False

    mock_issue = MagicMock()
    mock_issue.as_pull_request.return_value = pr
    mock_github_client.search_issues.return_value = [mock_issue]

    collector = PullRequestCollector(mock_github_client)
    prs = await collector.collect_user_prs(username="testuser")

    assert prs[0].organization == "my-org"
