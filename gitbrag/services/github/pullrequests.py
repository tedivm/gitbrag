"""Service for collecting GitHub pull request information."""

from datetime import datetime
from logging import getLogger

import httpx

from .client import GitHubAPIClient
from .models import PullRequestInfo
from .stargazers import collect_repository_star_increases

logger = getLogger(__name__)


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
                    )

                    pull_requests.append(pr_info)

                except (KeyError, ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse PR data: {e}", exc_info=True)
                    continue

            logger.info(f"Collected {len(pull_requests)} pull requests for user {username}")

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
