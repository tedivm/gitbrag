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

            max_retries = 3 if wait_for_rate_limit else 0
            result = await client.execute_graphql(query=query, variables=variables, max_retries=max_retries)

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

            # Check if there's another page (unless early termination triggered)
            if has_next_page:
                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

        logger.debug(f"Repository {owner}/{repo} gained {star_count} stars between {since} and {until}")

        # Cache the result
        await set_cached(cache_key, star_count, ttl=settings.cache_star_increase_ttl, alias="persistent")

        return star_count

    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            logger.warning(f"Rate limit hit for {owner}/{repo}: {e}")
        else:
            logger.warning(f"HTTP error fetching stars for {owner}/{repo}: {e}")
        return None
    except ValueError as e:
        logger.warning(f"GraphQL error fetching stars for {owner}/{repo}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching stars for {owner}/{repo}: {e}")
        return None


async def collect_repository_star_increases(
    client: GitHubAPIClient,
    repositories: list[str],
    since: datetime,
    until: datetime,
    wait_for_rate_limit: bool = True,
) -> dict[str, int | None]:
    """Collect star increases for multiple repositories concurrently.

    Args:
        client: Authenticated GitHub API client
        repositories: List of repository full names (e.g., "owner/repo")
        since: Start of time period
        until: End of time period
        wait_for_rate_limit: If True, wait when rate limited; if False, raise exception

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

    logger.debug(f"Collecting star increases for {len(unique_repos)} unique repositories")

    # Create tasks for concurrent fetching with repository names
    repo_tasks: list[tuple[str, Any]] = []
    for repo_full_name in unique_repos:
        parts = repo_full_name.split("/", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid repository name format: {repo_full_name}")
            continue
        owner, repo = parts
        task = fetch_repository_star_increase(
            client=client,
            owner=owner,
            repo=repo,
            since=since,
            until=until,
            wait_for_rate_limit=wait_for_rate_limit,
        )
        repo_tasks.append((repo_full_name, task))

    # Execute all tasks concurrently
    tasks = [task for _, task in repo_tasks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build result dictionary
    star_increases: dict[str, int | None] = {}
    for (repo_full_name, _), result in zip(repo_tasks, results):
        if isinstance(result, Exception):
            logger.error(f"Error collecting star increase for {repo_full_name}: {result}")
            star_increases[repo_full_name] = None
        elif isinstance(result, int):
            star_increases[repo_full_name] = result
            logger.debug(f"Repository {repo_full_name}: +{result} stars")
        else:
            star_increases[repo_full_name] = None
            logger.debug(f"Star increase unavailable for {repo_full_name}")

    return star_increases
