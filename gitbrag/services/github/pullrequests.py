"""Service for collecting GitHub pull request information."""

import asyncio
from datetime import datetime
from logging import getLogger

import httpx

from gitbrag.services.cache import get_cache

from .client import GitHubAPIClient
from .models import PullRequestInfo
from .stargazers import collect_repository_star_increases

logger = getLogger(__name__)

# Default TTL for PR file list caching (6 hours in seconds)
DEFAULT_FILE_LIST_TTL = 6 * 3600


async def fetch_pr_files(
    client: GitHubAPIClient,
    owner: str,
    repo: str,
    number: int,
    ttl: int = DEFAULT_FILE_LIST_TTL,
) -> tuple[list[str], int, int, int]:
    """Fetch file list and code change statistics for a pull request.

    Fetches the list of files changed in a PR and calculates aggregate code statistics.
    Results are cached with configurable TTL (default 6 hours).

    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        number: Pull request number
        ttl: Cache TTL in seconds (default 6 hours)

    Returns:
        Tuple of (file_names, additions, deletions, changed_files)
        where file_names is a list of filenames that changed

    Raises:
        httpx.HTTPStatusError: If GitHub API request fails
    """
    cache = get_cache("persistent")
    cache_key = f"pr_files:{owner}:{repo}:{number}"

    # Check cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        logger.debug(f"Cache hit for PR files: {owner}/{repo}#{number}")
        # Type check the cached data
        if (
            isinstance(cached_data, tuple)
            and len(cached_data) == 4
            and isinstance(cached_data[0], list)
            and isinstance(cached_data[1], int)
            and isinstance(cached_data[2], int)
            and isinstance(cached_data[3], int)
        ):
            return cached_data
        else:
            # Invalid cache data, fetch fresh
            logger.warning(f"Invalid cache data for {owner}/{repo}#{number}, fetching fresh")

    # Fetch from GitHub API
    try:
        files = await client.get_pr_files(owner=owner, repo=repo, number=number)

        # Extract file names and calculate aggregate statistics
        file_names: list[str] = []
        total_additions = 0
        total_deletions = 0

        for file in files:
            if "filename" in file:
                file_names.append(file["filename"])
            # Sum up per-file statistics
            total_additions += file.get("additions", 0)
            total_deletions += file.get("deletions", 0)

        changed_files = len(file_names)

        result = (file_names, total_additions, total_deletions, changed_files)

        # Cache the result
        await cache.set(cache_key, result, ttl=ttl)
        logger.debug(f"Cached PR files for {owner}/{repo}#{number} with TTL {ttl}s")

        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"PR not found: {owner}/{repo}#{number}")
            return ([], 0, 0, 0)
        else:
            logger.error(f"Failed to fetch PR files for {owner}/{repo}#{number}: {e}")
            # Return empty data on error rather than failing
            return ([], 0, 0, 0)
    except Exception as e:
        logger.error(f"Unexpected error fetching PR files for {owner}/{repo}#{number}: {e}", exc_info=True)
        return ([], 0, 0, 0)


class PullRequestCollector:
    """Service for collecting user's pull requests from GitHub."""

    def __init__(self, github_client: GitHubAPIClient) -> None:
        """Initialize the pull request collector.

        Args:
            github_client: Authenticated GitHub API client
        """
        self.github_client = github_client

    async def collect_user_prs(
        self,
        username: str,
        since: datetime | None = None,
        until: datetime | None = None,
        include_private: bool = False,
        include_star_increase: bool = False,
        wait_for_rate_limit: bool = True,
    ) -> list[PullRequestInfo]:
        """Collect pull requests for a given user.

        Args:
            username: GitHub username to collect PRs for
            since: Only include PRs created on or after this date
            until: Only include PRs created on or before this date
            include_private: Whether to include private repository PRs (default: False)
            include_star_increase: Whether to fetch star increase data for repositories (default: False)
            wait_for_rate_limit: If True, wait when rate limited; if False, raise exception (default: True)

        Returns:
            List of PullRequestInfo objects with optional star_increase field populated
            if include_star_increase is True

        Raises:
            httpx.HTTPStatusError: If GitHub API request fails
        """
        try:
            # Build search query
            query_parts = ["is:pr", f"author:{username}"]

            # Add date filters based on updated time (last activity)
            # This catches PRs created earlier but merged/updated in the time range
            # GitHub search API requires date ranges in YYYY-MM-DD..YYYY-MM-DD format
            if since and until:
                query_parts.append(f"updated:{since.strftime('%Y-%m-%d')}..{until.strftime('%Y-%m-%d')}")
            elif since:
                query_parts.append(f"updated:>={since.strftime('%Y-%m-%d')}")
            elif until:
                query_parts.append(f"updated:<={until.strftime('%Y-%m-%d')}")

            query = " ".join(query_parts)
            logger.debug(f"GitHub search query: {query}")

            # Execute search and get all results
            items = await self.github_client.search_all_issues(
                query=query,
                sort="updated",
                order="desc",
            )

            logger.debug(f"Found {len(items)} issues from search")

            # Convert to PullRequestInfo objects
            pull_requests: list[PullRequestInfo] = []

            for item in items:
                try:
                    # Check if this is actually a PR
                    if "pull_request" not in item or item["pull_request"] is None:
                        continue

                    # Extract repository information
                    repo_url = item.get("repository_url", "")
                    if repo_url:
                        repo_full_name = "/".join(repo_url.split("/")[-2:])
                    else:
                        # Fallback: parse from html_url
                        html_url = item.get("html_url", "")
                        url_parts = html_url.split("/")
                        repo_full_name = f"{url_parts[3]}/{url_parts[4]}"

                    # Extract organization from repository full name
                    repo_parts = repo_full_name.split("/")
                    organization = repo_parts[0] if len(repo_parts) > 1 else ""

                    # Parse timestamps
                    created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))

                    closed_at = None
                    if item.get("closed_at"):
                        closed_at = datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00"))

                    # Check if PR was merged
                    pr_data = item.get("pull_request", {})
                    merged_at = None
                    if pr_data.get("merged_at"):
                        merged_at = datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00"))

                    # Determine if PR is from a private repo
                    # Note: GitHub search API doesn't directly expose repository visibility
                    # We'll assume public unless we can determine otherwise
                    is_private = False

                    # Skip private repos if not requested
                    if is_private and not include_private:
                        logger.debug(f"Skipping private PR: {repo_full_name}#{item['number']}")
                        continue

                    # Extract author_association from search API response
                    author_association = item.get("author_association")

                    pr_info = PullRequestInfo(
                        number=item["number"],
                        title=item["title"],
                        repository=repo_full_name,
                        organization=organization,
                        author=item["user"]["login"],
                        state=item["state"],
                        created_at=created_at,
                        closed_at=closed_at,
                        merged_at=merged_at,
                        url=item["html_url"],
                        author_association=author_association,
                    )

                    pull_requests.append(pr_info)

                except (KeyError, ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse PR data: {e}", exc_info=True)
                    continue

            logger.info(f"Collected {len(pull_requests)} pull requests for user {username}")

            # Fetch file lists and code metrics for all PRs with limited concurrency
            if pull_requests:
                logger.debug(f"Fetching file lists for {len(pull_requests)} PRs")

                semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

                async def fetch_pr_metrics(pr: PullRequestInfo) -> None:
                    """Fetch and populate code metrics for a single PR."""
                    async with semaphore:
                        try:
                            repo_parts = pr.repository.split("/", 1)
                            if len(repo_parts) != 2:
                                return

                            owner, repo = repo_parts
                            file_names, additions, deletions, changed_files = await fetch_pr_files(
                                client=self.github_client,
                                owner=owner,
                                repo=repo,
                                number=pr.number,
                            )

                            # Populate the PR info with metrics
                            pr.additions = additions
                            pr.deletions = deletions
                            pr.changed_files = changed_files

                        except Exception as e:
                            logger.warning(f"Failed to fetch files for PR {pr.repository}#{pr.number}: {e}")

                # Fetch all PR metrics concurrently
                await asyncio.gather(*[fetch_pr_metrics(pr) for pr in pull_requests])

            # Optionally collect star increases for repositories
            if include_star_increase and since and until:
                # Extract unique repository names from PRs
                repositories = list({pr.repository for pr in pull_requests})
                if repositories:
                    logger.debug(f"Collecting star increases for {len(repositories)} repositories")
                    star_increases = await collect_repository_star_increases(
                        client=self.github_client,
                        repositories=repositories,
                        since=since,
                        until=until,
                        wait_for_rate_limit=wait_for_rate_limit,
                    )
                    # Populate star_increase field in each PR
                    for pr in pull_requests:
                        pr.star_increase = star_increases.get(pr.repository)

            return pull_requests

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"User not found: {username}")
                return []
            elif e.response.status_code == 422:
                # Unprocessable entity - usually means invalid search query or nonexistent user
                logger.warning(f"Invalid search query or user not found: {username}")
                return []
            elif e.response.status_code == 403:
                logger.error(f"Access forbidden - check token permissions: {e}")
                raise
            else:
                logger.error(f"GitHub API error: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error collecting pull requests: {e}", exc_info=True)
            raise
