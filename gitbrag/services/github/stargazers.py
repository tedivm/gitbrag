"""GitHub stargazer fetching and star increase calculation."""

import asyncio
from datetime import datetime
from logging import getLogger
from typing import Any

import httpx

from gitbrag.services.cache import get_cached, set_cached
from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.settings import settings

logger = getLogger(__name__)


async def fetch_repository_star_increase(
    client: GitHubAPIClient,
    owner: str,
    repo: str,
    since: datetime,
    until: datetime,
    wait_for_rate_limit: bool = True,
) -> int | None:
    """Fetch the number of stars added to a repository during a time period.

    Uses GitHub's GraphQL API to fetch stargazer timestamps and count those
    within the specified date range. Implements pagination with early termination
    when starredAt timestamps are before the since date.

    Results are cached for 24 hours since historical data doesn't change.

    Args:
        client: Authenticated GitHub API client
        owner: Repository owner (user or organization)
        repo: Repository name
        since: Start of time period
        until: End of time period
        wait_for_rate_limit: If True, wait when rate limited; if False, raise exception

    Returns:
        Number of stars added during the time period, or None if data unavailable

    Raises:
        httpx.HTTPStatusError: If the request fails and wait_for_rate_limit is False
    """
    # Check cache first
    cache_key = f"repo:{owner}/{repo}:star_increase:{since.isoformat()}:{until.isoformat()}"
    cached_result = await get_cached(cache_key, alias="persistent")
    if cached_result is not None:
        logger.debug(f"Cache hit for {owner}/{repo} star increase")
        assert isinstance(cached_result, int)
        return cached_result

    # Optimization: For all-time queries (since before GitHub's launch in 2008),
    # just use the total stargazer count instead of paginating through all stars
    github_launch = datetime(2008, 1, 1, tzinfo=since.tzinfo)
    if since <= github_launch:
        logger.debug(f"All-time query for {owner}/{repo}, using total stargazer count")
        try:
            repo_info = await client.get_repository(owner, repo)
            total_stars: int | None = repo_info.get("stargazers_count", 0)
            logger.debug(f"Repository {owner}/{repo} has {total_stars} total stars")

            # Cache the result
            await set_cached(cache_key, total_stars, ttl=settings.cache_star_increase_ttl, alias="persistent")
            return total_stars
        except Exception as e:
            logger.error(f"Failed to fetch total star count for {owner}/{repo}: {e}")
            return None

    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        stargazers(first: 100, after: $cursor, orderBy: {field: STARRED_AT, direction: DESC}) {
          pageInfo {
            endCursor
            hasNextPage
          }
          edges {
            starredAt
          }
        }
      }
    }
    """

    star_count = 0
    cursor = None
    has_next_page = True

    try:
        while has_next_page:
            variables: dict[str, Any] = {"owner": owner, "name": repo}
            if cursor:
                variables["cursor"] = cursor

            result = await client.execute_graphql(query=query, variables=variables)

            # Extract repository data
            repo_data = result.get("data", {}).get("repository")
            if not repo_data:
                logger.warning(f"Repository {owner}/{repo} not found or inaccessible")
                return None

            stargazers = repo_data.get("stargazers", {})
            edges = stargazers.get("edges", [])
            page_info = stargazers.get("pageInfo", {})

            # Count stars in date range and check for early termination
            for edge in edges:
                starred_at_str = edge.get("starredAt")
                if not starred_at_str:
                    continue

                starred_at = datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))

                # Early termination: if we've gone past the since date, stop
                if starred_at < since:
                    logger.debug(f"Early termination for {owner}/{repo} at {starred_at}")
                    has_next_page = False
                    break

                # Count stars within the date range
                if since <= starred_at <= until:
                    star_count += 1
                    # Early termination at 1000 stars for performance
                    if star_count >= 1000:
                        logger.debug(f"Star count limit reached for {owner}/{repo} (>1000 stars)")
                        # Return -1 to indicate >1000 stars
                        await set_cached(cache_key, -1, ttl=settings.cache_star_increase_ttl, alias="persistent")
                        return -1

            # Check if there's another page (unless early termination triggered)
            if has_next_page:
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

        logger.debug(f"Repository {owner}/{repo} gained {star_count} stars between {since} and {until}")

        # Cache the result
        await set_cached(cache_key, star_count, ttl=settings.cache_star_increase_ttl, alias="persistent")

        return star_count

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching stars for {owner}/{repo} after retries")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            logger.warning(f"Rate limit hit for {owner}/{repo}: {e.response.status_code}")
        else:
            logger.warning(f"HTTP error fetching stars for {owner}/{repo}: {e.response.status_code}")
        return None
    except ValueError as e:
        logger.warning(f"GraphQL error fetching stars for {owner}/{repo}: {e}")
        return None
    except Exception:
        logger.exception(f"Unexpected error fetching stars for {owner}/{repo}")
        return None


async def collect_repository_star_increases(
    client: GitHubAPIClient,
    repositories: list[str],
    since: datetime,
    until: datetime,
    wait_for_rate_limit: bool = True,
    max_concurrent: int = 10,
) -> dict[str, int | None]:
    """Collect star increases for multiple repositories concurrently.

    Args:
        client: Authenticated GitHub API client
        repositories: List of repository full names (e.g., "owner/repo")
        since: Start of time period
        until: End of time period
        wait_for_rate_limit: If True, wait when rate limited; if False, raise exception
        max_concurrent: Maximum number of concurrent repository fetches (default: 10)

    Returns:
        Dictionary mapping repository name to star increase (or None if unavailable)
    """
    # Deduplicate repositories while preserving order
    seen = set()
    unique_repos = []
    for repo in repositories:
        if repo not in seen:
            seen.add(repo)
            unique_repos.append(repo)

    logger.debug(
        f"Collecting star increases for {len(unique_repos)} unique repositories (max {max_concurrent} concurrent)"
    )

    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(repo_full_name: str) -> tuple[str, int | None]:
        """Fetch star increase with semaphore limiting concurrency."""
        parts = repo_full_name.split("/", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid repository name format: {repo_full_name}")
            return repo_full_name, None

        owner, repo = parts
        async with semaphore:
            try:
                result = await fetch_repository_star_increase(
                    client=client,
                    owner=owner,
                    repo=repo,
                    since=since,
                    until=until,
                    wait_for_rate_limit=wait_for_rate_limit,
                )
                return repo_full_name, result
            except Exception as e:
                logger.exception(f"Error collecting star increase for {repo_full_name}", exc_info=e)
                return repo_full_name, None

    # Create tasks for all repositories
    tasks = [fetch_with_semaphore(repo_full_name) for repo_full_name in unique_repos]

    # Execute with limited concurrency
    results = await asyncio.gather(*tasks)

    # Build result dictionary
    star_increases: dict[str, int | None] = {}
    for repo_full_name, result in results:
        star_increases[repo_full_name] = result
        if result is not None:
            logger.debug(f"Repository {repo_full_name}: +{result} stars")
        else:
            logger.debug(f"Star increase unavailable for {repo_full_name}")

    return star_increases
