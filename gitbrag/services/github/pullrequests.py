"""Service for collecting GitHub pull request information."""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger

import httpx

from gitbrag.conf.github import get_github_settings
from gitbrag.services.cache import get_cache

from .client import GitHubAPIClient
from .models import PullRequestInfo
from .stargazers import collect_repository_star_increases

logger = getLogger(__name__)

# Default TTL for PR file list caching (6 hours in seconds)
DEFAULT_FILE_LIST_TTL = 6 * 3600


@dataclass
class CollectionStats:
    """Statistics tracking for PR collection operations."""

    total_prs: int = 0
    file_fetch_success: int = 0
    file_fetch_failed: int = 0
    file_fetch_cached: int = 0
    failed_prs: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate for file fetching operations.

        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        total_attempts = self.file_fetch_success + self.file_fetch_failed
        if total_attempts == 0:
            return 1.0
        return self.file_fetch_success / total_attempts


def categorize_error(error: Exception) -> str:
    """Categorize an error as transient or fatal for retry logic.

    Args:
        error: The exception to categorize

    Returns:
        "transient" for errors that should be retried, "fatal" for permanent failures

    Examples:
        >>> categorize_error(httpx.TimeoutException("timeout"))
        'transient'
        >>> categorize_error(httpx.HTTPStatusError("404", request=..., response=...))
        'fatal'
    """
    # Timeout and connection errors are transient
    if isinstance(error, httpx.TimeoutException):
        return "transient"
    if isinstance(error, httpx.ConnectError):
        return "transient"

    # HTTP errors need case-by-case analysis
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code

        # Fatal errors that should not be retried
        if status_code in (401, 403, 404, 422):
            return "fatal"

        # Transient errors that should be retried
        if status_code in (429, 500, 502, 503, 504):
            return "transient"

        # Default HTTP errors to transient
        return "transient"

    # Unknown errors default to transient (conservative approach)
    return "transient"


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
        # Type check and validate the cached data
        if (
            isinstance(cached_data, tuple)
            and len(cached_data) == 4
            and isinstance(cached_data[0], list)
            and isinstance(cached_data[1], int)
            and isinstance(cached_data[2], int)
            and isinstance(cached_data[3], int)
        ):
            # Validate non-negative values
            cached_file_names, cached_additions, cached_deletions, cached_changed_files = cached_data
            if cached_additions < 0 or cached_deletions < 0 or cached_changed_files < 0:
                logger.warning(
                    f"Invalid cached data for {owner}/{repo}#{number}: "
                    f"negative values (additions={cached_additions}, deletions={cached_deletions}, files={cached_changed_files}). "
                    f"Refetching from API."
                )
            else:
                return cached_data
        else:
            # Invalid cache data, fetch fresh
            logger.warning(
                f"Invalid cache data for {owner}/{repo}#{number}, fetching fresh. "
                f"Expected tuple[list, int, int, int], got {type(cached_data)}"
            )

    # Fetch from GitHub API
    logger.debug(f"Fetching PR files from API: {owner}/{repo}#{number}")
    try:
        files = await client.get_pr_files(owner=owner, repo=repo, number=number)

        # Extract file names and calculate aggregate statistics
        file_names: list[str] = []
        total_additions = 0
        total_deletions = 0

        for file in files:
            if "filename" in file:
                file_names.append(file["filename"])
            # Sum up per-file statistics, ensuring non-negative values
            file_additions = max(0, file.get("additions", 0))
            file_deletions = max(0, file.get("deletions", 0))
            total_additions += file_additions
            total_deletions += file_deletions

            # Log warning if negative values were found and clamped
            if file.get("additions", 0) < 0 or file.get("deletions", 0) < 0:
                logger.warning(
                    f"Negative values in file data for {owner}/{repo}#{number}, "
                    f"file: {file.get('filename', 'unknown')}, clamping to 0"
                )

        changed_files = len(file_names)

        result = (file_names, total_additions, total_deletions, changed_files)

        # Cache the result
        await cache.set(cache_key, result, ttl=ttl)
        logger.debug(
            f"Fetched and cached PR files for {owner}/{repo}#{number}: "
            f"+{total_additions} -{total_deletions} files={changed_files} (TTL {ttl}s)"
        )

        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(
                f"PR not found (404): {owner}/{repo}#{number}. This is expected for deleted PRs. Returning empty data."
            )
            return ([], 0, 0, 0)
        else:
            logger.error(
                f"HTTP error {e.response.status_code} fetching PR files for {owner}/{repo}#{number}: {e}. "
                f"Returning empty data."
            )
            # Return empty data on error rather than failing
            return ([], 0, 0, 0)
    except Exception as e:
        logger.error(
            f"Unexpected error fetching PR files for {owner}/{repo}#{number}: {e}. Returning empty data.",
            exc_info=True,
        )
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
        import time

        collection_start_time = time.time()
        logger.info(f"Starting PR collection for {username} from {since} to {until}")

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
            search_start_time = time.time()
            items = await self.github_client.search_all_issues(
                query=query,
                sort="updated",
                order="desc",
            )
            search_duration = time.time() - search_start_time

            logger.info(f"GitHub search completed in {search_duration:.2f}s: found {len(items)} issues")

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

            # Initialize collection statistics
            stats = CollectionStats(total_prs=len(pull_requests))

            # Fetch file lists and code metrics for all PRs with limited concurrency
            if pull_requests:
                # Get configured concurrency limit
                settings = get_github_settings()
                concurrency_limit = settings.github_pr_file_fetch_concurrency
                logger.info(
                    f"Fetching file lists for {len(pull_requests)} PRs with concurrency limit of {concurrency_limit}"
                )

                file_fetch_start_time = time.time()
                semaphore = asyncio.Semaphore(concurrency_limit)

                async def fetch_pr_metrics(pr: PullRequestInfo) -> None:
                    """Fetch and populate code metrics for a single PR with retry logic."""
                    max_retries = 3
                    base_delays = [1, 2, 4]  # Exponential backoff base

                    async with semaphore:
                        for attempt in range(max_retries + 1):
                            try:
                                repo_parts = pr.repository.split("/", 1)
                                if len(repo_parts) != 2:
                                    return

                                owner, repo = repo_parts

                                # Check if data is cached before attempting fetch
                                cache = get_cache("persistent")
                                cache_key = f"pr_files:{owner}:{repo}:{pr.number}"
                                cached_data = await cache.get(cache_key)
                                is_cached = cached_data is not None

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

                                # Track success
                                if is_cached:
                                    stats.file_fetch_cached += 1
                                else:
                                    stats.file_fetch_success += 1
                                return

                            except Exception as e:
                                error_type = categorize_error(e)

                                # Check if we should retry
                                if error_type == "fatal" or attempt == max_retries:
                                    logger.error(
                                        f"Failed to fetch files for PR {pr.repository}#{pr.number} "
                                        f"after {attempt + 1} attempts: {e}"
                                    )
                                    stats.file_fetch_failed += 1
                                    stats.failed_prs.append(f"{pr.repository}#{pr.number}")
                                    return

                                # Transient error - retry with exponential backoff + jitter
                                base_delay = base_delays[attempt]
                                jitter = random.uniform(-0.25, 0.25) * base_delay
                                wait_time = base_delay + jitter
                                logger.warning(
                                    f"Transient error fetching PR {pr.repository}#{pr.number} "
                                    f"(attempt {attempt + 1}/{max_retries}), retrying in {wait_time:.2f}s: {e}"
                                )
                                await asyncio.sleep(wait_time)

                # Fetch all PR metrics concurrently
                await asyncio.gather(*[fetch_pr_metrics(pr) for pr in pull_requests])

                file_fetch_duration = time.time() - file_fetch_start_time

                # Log summary statistics
                logger.info(
                    f"File fetch complete in {file_fetch_duration:.2f}s: "
                    f"{stats.file_fetch_success} succeeded, "
                    f"{stats.file_fetch_cached} cached, {stats.file_fetch_failed} failed "
                    f"(success rate: {stats.success_rate:.1%})"
                )

                # Warn or error based on failure rate
                if stats.file_fetch_failed > 0:
                    failure_rate = stats.file_fetch_failed / stats.total_prs if stats.total_prs > 0 else 0
                    if failure_rate > 0.1:
                        logger.error(
                            f"High failure rate: {stats.file_fetch_failed}/{stats.total_prs} PRs "
                            f"({failure_rate:.1%}) failed to fetch file data. "
                            f"Consider reducing concurrency or checking API rate limits."
                        )
                        if stats.failed_prs[:5]:  # Show first 5 failed PRs
                            logger.error(f"First failed PRs: {', '.join(stats.failed_prs[:5])}")
                    else:
                        logger.warning(
                            f"Some PRs failed: {stats.file_fetch_failed}/{stats.total_prs} "
                            f"({failure_rate:.1%}). Failed PRs: {', '.join(stats.failed_prs[:5])}"
                        )

            # Optionally collect star increases for repositories
            if include_star_increase and since and until:
                # Extract unique repository names from PRs
                repositories = list({pr.repository for pr in pull_requests})
                if repositories:
                    star_fetch_start_time = time.time()
                    logger.info(f"Collecting star increases for {len(repositories)} repositories")
                    star_increases = await collect_repository_star_increases(
                        client=self.github_client,
                        repositories=repositories,
                        since=since,
                        until=until,
                        wait_for_rate_limit=wait_for_rate_limit,
                    )
                    star_fetch_duration = time.time() - star_fetch_start_time
                    logger.info(f"Star increase collection completed in {star_fetch_duration:.2f}s")
                    # Populate star_increase field in each PR
                    for pr in pull_requests:
                        pr.star_increase = star_increases.get(pr.repository)

            total_duration = time.time() - collection_start_time
            logger.info(
                f"PR collection completed for {username} in {total_duration:.2f}s: {len(pull_requests)} PRs collected"
            )

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
