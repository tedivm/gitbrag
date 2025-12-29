"""Report generation service for web interface.

This module generates contribution reports by collecting PRs and
organizing them for display.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Any

from pydantic import SecretStr

from gitbrag.services.cache import get_cache
from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.services.github.models import PullRequestInfo
from gitbrag.services.github.pullrequests import PullRequestCollector
from gitbrag.services.language_analyzer import calculate_language_percentages
from gitbrag.services.pr_size import categorize_pr_size

logger = getLogger(__name__)


def normalize_period(period: str | None) -> str:
    """Normalize period parameter to standard name.

    Args:
        period: Period string (1_year, 2_years, 5_years, all_time, or None)

    Returns:
        Normalized period name
    """
    if not period:
        return "1_year"

    period = period.lower().strip()
    logger.debug(f"Normalizing period: '{period}'")
    if period in ("1_year", "2_years", "5_years", "all_time"):
        logger.debug(f"Normalized period result: '{period}'")
        return period

    logger.debug(f"Period '{period}' not recognized, defaulting to '1_year'")
    return "1_year"  # Default fallback


def calculate_date_range(period: str) -> tuple[datetime, datetime]:
    """Calculate date range from period name.

    Args:
        period: Normalized period name

    Returns:
        Tuple of (since, until) datetime objects (timezone-aware)
    """
    until = datetime.now(tz=timezone.utc)

    if period == "1_year":
        since = until - timedelta(days=365)
    elif period == "2_years":
        since = until - timedelta(days=730)
    elif period == "5_years":
        since = until - timedelta(days=1825)
    elif period == "all_time":
        # GitHub launched in 2008, use that as earliest date
        since = datetime(2008, 1, 1, tzinfo=timezone.utc)
    else:
        since = until - timedelta(days=365)

    return since, until


def generate_cache_key(username: str, period: str, show_star_increase: bool = False) -> str:
    """Generate a cache key for a user's report.

    Args:
        username: GitHub username
        period: Period name (1_month, 3_months, etc.)
        show_star_increase: Whether star increase data is included

    Returns:
        Cache key string
    """
    # Normalize username to lowercase for consistent cache keys
    username = username.lower()

    # Create hash of parameters
    params = {"show_star_increase": show_star_increase}
    params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]

    return f"report:{username}:{period}:{params_hash}"


async def get_or_fetch_user_profile(
    username: str,
    token: str | None = None,
) -> dict[str, Any] | None:
    """Get user profile from cache or fetch from GitHub if authenticated.

    Profile is cached permanently (no expiration). If an authenticated user requests
    the profile and the cached version is older than 1 hour, it will be refreshed.

    Args:
        username: GitHub username
        token: GitHub API token (None if unauthenticated)

    Returns:
        User profile dictionary or None if not available
    """
    # Normalize username to lowercase for consistent cache keys
    # (GitHub API will still receive original case, as it's case-preserving)
    username_lower = username.lower()

    cache = get_cache("persistent")
    cache_key = f"profile:{username_lower}"
    meta_key = f"{cache_key}:meta"

    # Try to get from cache first
    cached_profile = await cache.get(cache_key)
    cached_meta = await cache.get(meta_key)

    if cached_profile:
        # Check if we should refresh (only if authenticated and cache is old)
        should_refresh = False
        if token and cached_meta:
            cache_age = datetime.now().timestamp() - cached_meta.get("cached_at", 0)
            # Refresh if older than 1 hour (3600 seconds)
            if cache_age >= 3600:
                should_refresh = True
                logger.debug(f"Profile cache for {username} is {cache_age:.0f}s old, refreshing")

        if not should_refresh:
            logger.debug(f"Using cached profile for {username}")
            # Explicitly cast to expected type
            return dict(cached_profile) if isinstance(cached_profile, dict) else None

    # Fetch from GitHub if we have a token (either no cache or refresh needed)
    if token:
        try:
            # Create a new client with the token
            async with GitHubAPIClient(token=SecretStr(token)) as client:
                profile = await client.get_user(username)
                if profile:
                    # Fetch social accounts and merge into profile
                    try:
                        social_accounts = await client.get_user_social_accounts(username)
                        profile["social_accounts"] = social_accounts
                        logger.debug(f"Fetched {len(social_accounts)} social accounts for {username}")
                    except Exception as e:
                        # Log but don't fail if social accounts fetch fails
                        logger.warning(f"Failed to fetch social accounts for {username}: {e}")
                        profile["social_accounts"] = []

                    # Cache permanently (no TTL)
                    metadata = {"cached_at": datetime.now().timestamp()}
                    await cache.set(cache_key, profile)
                    await cache.set(meta_key, metadata)
                    logger.debug(f"Fetched and cached profile for {username}")
                    return profile
        except Exception as e:
            logger.warning(f"Failed to fetch user profile for {username}: {e}")
            # If we had a cached version, return it even if stale
            if cached_profile:
                logger.debug(f"Returning stale cached profile for {username} after fetch failure")
                return dict(cached_profile) if isinstance(cached_profile, dict) else None

    return None


async def generate_report_data(
    github_client: GitHubAPIClient,
    username: str,
    since: datetime,
    until: datetime,
    show_star_increase: bool = False,
    period: str | None = None,
    exclude_closed_unmerged: bool = True,
) -> dict[str, Any]:
    """Generate report data for a user.

    Args:
        github_client: Authenticated GitHub client
        username: GitHub username
        since: Start date for PR collection
        until: End date for PR collection
        show_star_increase: Whether to include star increase data
        period: Optional period name for sorting logic (1_year, 2_years, all_time)
        exclude_closed_unmerged: Whether to exclude closed-but-not-merged PRs (default True for web)

    Returns:
        Dictionary with report data
    """
    logger.info(f"Generating report for {username} from {since.date()} to {until.date()}")

    # Collect PRs and fetch repository descriptions - client must be used with context manager
    async with github_client:
        collector = PullRequestCollector(github_client)
        prs = await collector.collect_user_prs(
            username=username,
            since=since,
            until=until,
            include_private=False,
            include_star_increase=show_star_increase,
        )

        logger.info(f"Collected {len(prs)} PRs for {username}")

        # Filter out closed-but-not-merged PRs if requested
        if exclude_closed_unmerged:
            original_count = len(prs)
            prs = [pr for pr in prs if pr.get_display_state() != "closed"]
            filtered_count = original_count - len(prs)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} closed-but-not-merged PRs")

        # Calculate statistics
        total_prs = len(prs)
        merged_count = sum(1 for pr in prs if pr.get_display_state() == "merged")
        open_count = sum(1 for pr in prs if pr.get_display_state() == "open")
        closed_count = sum(1 for pr in prs if pr.get_display_state() == "closed")

        # Calculate aggregate code metrics
        total_additions = sum(pr.additions or 0 for pr in prs)
        total_deletions = sum(pr.deletions or 0 for pr in prs)
        total_changed_files = sum(pr.changed_files or 0 for pr in prs)

        # Calculate language breakdown
        language_breakdown = await calculate_language_percentages(prs, top_n=10)

        # Group by repository
        repos: dict[str, list] = {}
        for pr in prs:
            repo_full_name = pr.repository
            if repo_full_name not in repos:
                repos[repo_full_name] = []
            repos[repo_full_name].append(pr)

        # Calculate repository-level author associations (from most recent PR per repo)
        repo_roles: dict[str, str | None] = {}
        for repo_name, repo_prs in repos.items():
            # Most recent PR based on created_at
            most_recent = max(repo_prs, key=lambda pr: pr.created_at)
            repo_roles[repo_name] = most_recent.author_association

        # Calculate PR size categories for each PR
        for pr in prs:
            pr.size_category = categorize_pr_size(pr.additions, pr.deletions)  # type: ignore[attr-defined]

        # Calculate PR size distribution
        from collections import Counter

        size_distribution: dict[str, int] = Counter()
        for pr in prs:
            size_cat = getattr(pr, "size_category", None)
            if size_cat:
                size_distribution[size_cat] += 1

        # Order by size category (One Liner -> Massive)
        size_order = ["One Liner", "Small", "Medium", "Large", "Huge", "Massive"]
        ordered_distribution = {
            size: size_distribution.get(size, 0) for size in size_order if size in size_distribution
        }

        # Sort repositories by star increase (descending), then by name
        # For all_time period, sort by number of PRs instead
        if period == "all_time":
            # Sort by number of PRs per repo (descending), then by repo name
            repos = dict(sorted(repos.items(), key=lambda x: (-len(x[1]), x[0])))
        elif show_star_increase:
            # Get star increase for each repo (use first PR's star_increase since they're all the same per repo)
            # Treat -1 (>1000) as higher than any actual count for sorting purposes
            def get_sort_key(repo_prs_tuple: tuple[str, list[PullRequestInfo]]) -> tuple[int, str]:
                repo, prs = repo_prs_tuple
                star_value = prs[0].star_increase or 0
                # If star_increase is -1 (>1000), treat as 1001 for sorting
                sort_value = 1001 if star_value == -1 else star_value
                return (-sort_value, repo)

            repos = dict(sorted(repos.items(), key=get_sort_key))
        else:
            # Sort alphabetically by repository name
            repos = dict(sorted(repos.items()))

        repo_count = len(repos)

        # Fetch repository descriptions
        repo_descriptions: dict[str, str | None] = {}
        unique_repos = list(repos.keys())
        if unique_repos:
            logger.debug(f"Fetching descriptions for {len(unique_repos)} repositories")

            async def fetch_repo_description(repo_full_name: str) -> tuple[str, str | None]:
                """Fetch description for a single repository."""
                parts = repo_full_name.split("/", 1)
                if len(parts) != 2:
                    return repo_full_name, None

                owner, repo = parts
                try:
                    repo_info = await github_client.get_repository(owner, repo)
                    description = repo_info.get("description")
                    return repo_full_name, description
                except Exception as e:
                    logger.warning(f"Failed to fetch description for {repo_full_name}: {e}")
                    return repo_full_name, None

            # Fetch all descriptions concurrently with limited parallelism
            import asyncio

            semaphore = asyncio.Semaphore(10)

            async def fetch_with_semaphore(repo_name: str) -> tuple[str, str | None]:
                async with semaphore:
                    return await fetch_repo_description(repo_name)

            tasks = [fetch_with_semaphore(repo_name) for repo_name in unique_repos]
            results = await asyncio.gather(*tasks)

            for repo_name, description in results:
                repo_descriptions[repo_name] = description

    # Calculate total star increase if requested
    total_star_increase = 0
    if show_star_increase:
        # If any repo has >1000 stars (-1), set total to -1 to indicate >1000
        has_over_1000 = any(pr.star_increase == -1 for pr in prs)
        if has_over_1000:
            total_star_increase = -1
        else:
            total_star_increase = sum(pr.star_increase or 0 for pr in prs)

    return {
        "username": username,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "total_prs": total_prs,
        "merged_count": merged_count,
        "open_count": open_count,
        "closed_count": closed_count,
        "repo_count": repo_count,
        "total_star_increase": total_star_increase if show_star_increase else None,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "total_changed_files": total_changed_files,
        "language_breakdown": language_breakdown,
        "repo_roles": repo_roles,
        "size_distribution": ordered_distribution,
        "repositories": repos,
        "repo_descriptions": repo_descriptions,
        "prs": prs,
    }
