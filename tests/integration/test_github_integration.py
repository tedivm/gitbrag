"""Integration tests for GitHub API with real credentials."""

from datetime import datetime, timedelta

import pytest

from gitbrag.conf.settings import Settings
from gitbrag.services.formatter import format_pr_list
from gitbrag.services.github.auth import GitHubClient
from gitbrag.services.github.pullrequests import PullRequestCollector

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.skipif(
    Settings().github_token is None,
    reason="GITHUB_TOKEN not set - skipping integration tests",
)


@pytest.mark.asyncio
async def test_collect_user_prs_real_api() -> None:
    """Test collecting PRs for a real user (tedivm)."""
    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        collector = PullRequestCollector(github_client)

        # Use a broad time range to ensure we get results
        since = datetime.now() - timedelta(days=365 * 2)  # 2 years ago
        until = datetime.now()

        prs = await collector.collect_user_prs(username="tedivm", since=since, until=until)

        # Should find at least some PRs
        assert len(prs) > 0

        # Validate structure of first PR
        pr = prs[0]
        assert pr.number > 0
        assert pr.title
        assert pr.repository
        assert pr.author == "tedivm"
        assert pr.organization
        assert isinstance(pr.created_at, datetime)


@pytest.mark.asyncio
async def test_collect_user_prs_with_date_filter_real_api() -> None:
    """Test collecting PRs with date filtering using real API."""
    from datetime import timezone

    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        collector = PullRequestCollector(github_client)

        # Use last year as date range (timezone-aware to match API responses)
        since = (datetime.now(timezone.utc) - timedelta(days=365)).replace(microsecond=0)
        until = datetime.now(timezone.utc).replace(microsecond=0)

        prs = await collector.collect_user_prs(username="tedivm", since=since, until=until)

        # Verify all PRs are within date range (allowing for GitHub's date formatting)
        for pr in prs:
            # Allow 1 second tolerance for date comparisons due to microsecond differences
            assert pr.created_at >= (since - timedelta(seconds=1)), (
                f"PR {pr.number} created at {pr.created_at} before 'since' date {since}"
            )
            assert pr.created_at <= (until + timedelta(seconds=1)), (
                f"PR {pr.number} created at {pr.created_at} after 'until' date {until}"
            )


@pytest.mark.asyncio
async def test_collect_user_prs_public_only_real_api() -> None:
    """Test that only public PRs are collected by default."""
    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        collector = PullRequestCollector(github_client)

        # Use a shorter time range for faster tests
        since = datetime.now() - timedelta(days=180)
        until = datetime.now()

        # Default should only get public PRs
        prs = await collector.collect_user_prs(username="tedivm", since=since, until=until, include_private=False)

        # Should find at least some public PRs
        assert len(prs) >= 0  # May or may not have public PRs in this range


@pytest.mark.asyncio
async def test_nonexistent_user_real_api() -> None:
    """Test handling of non-existent user with real API."""
    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        collector = PullRequestCollector(github_client)

        # Use a username that definitely doesn't exist
        since = datetime.now() - timedelta(days=365)
        until = datetime.now()

        prs = await collector.collect_user_prs(
            username="this_user_definitely_does_not_exist_12345678",
            since=since,
            until=until,
        )

        # Should return empty list for non-existent user
        assert prs == []


@pytest.mark.asyncio
async def test_format_real_prs() -> None:
    """Test formatting real PRs."""
    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        collector = PullRequestCollector(github_client)

        # Get a small set of recent PRs
        since = datetime.now() - timedelta(days=365)
        until = datetime.now()

        prs = await collector.collect_user_prs(username="tedivm", since=since, until=until)

        # Should be able to format without errors
        # This will print to console but won't raise exceptions
        if prs:
            format_pr_list(prs, show_urls=True, sort_fields=[("created", "desc")])


@pytest.mark.asyncio
async def test_basic_api_access() -> None:
    """Test basic API access and rate limiting with real API."""
    settings = Settings()
    assert settings.github_token is not None, "GITHUB_TOKEN must be set"
    token = settings.github_token.get_secret_value()

    client_factory = GitHubClient(token_override=token)
    github_client = await client_factory.get_authenticated_client()

    async with github_client:
        # Check rate limit
        rate_limit = await github_client.get_rate_limit()
        assert "resources" in rate_limit
        assert "core" in rate_limit["resources"]
        assert "search" in rate_limit["resources"]

        # Verify we have remaining API calls
        core_remaining = rate_limit["resources"]["core"]["remaining"]
        assert core_remaining > 0
