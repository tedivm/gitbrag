"""Async GitHub API client using httpx."""

import asyncio
from logging import getLogger
from typing import Any

import httpx
from pydantic import SecretStr

logger = getLogger(__name__)


class GitHubAPIClient:
    """Async GitHub API client for making API requests."""

    def __init__(self, token: SecretStr, base_url: str = "https://api.github.com") -> None:
        """Initialize GitHub API client.

        Args:
            token: GitHub Personal Access Token
            base_url: Base URL for GitHub API (default: https://api.github.com)
        """
        self.token = token.get_secret_value()
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubAPIClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        retry_count: int = 0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with automatic retry on timeout and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            max_retries: Maximum number of retries
            retry_count: Current retry attempt (internal use)
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: If the request fails after retries
            httpx.TimeoutException: If request times out after retries
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async with context manager")

        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except httpx.TimeoutException:
            # Retry on timeout with exponential backoff
            if retry_count < max_retries:
                wait_time = 2**retry_count  # 1, 2, 4 seconds
                logger.warning(
                    f"Timeout on {method} {url} (attempt {retry_count + 1}/{max_retries}). "
                    f"Waiting {wait_time} seconds before retry..."
                )
                await asyncio.sleep(wait_time)
                return await self._request_with_retry(method, url, max_retries, retry_count + 1, **kwargs)
            # Re-raise if max retries exceeded
            logger.error(f"{method} {url} failed after {max_retries} retries due to timeout")
            raise

        except httpx.HTTPStatusError as e:
            # Handle rate limiting (403 or 429)
            if e.response.status_code in (403, 429) and retry_count < max_retries:
                reset_time = e.response.headers.get("X-RateLimit-Reset")
                remaining = e.response.headers.get("X-RateLimit-Remaining", "")
                is_rate_limit = e.response.status_code == 429 or remaining == "0"

                if is_rate_limit:
                    if reset_time:
                        import time

                        wait_time = min(int(reset_time) - int(time.time()), 60)
                        wait_time = max(wait_time, 1)
                    else:
                        wait_time = 2**retry_count

                    logger.warning(
                        f"Rate limit hit on {method} {url} (attempt {retry_count + 1}/{max_retries}). "
                        f"Waiting {wait_time} seconds before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request_with_retry(method, url, max_retries, retry_count + 1, **kwargs)
            # Re-raise if not rate limit or max retries exceeded
            raise

    async def get_authenticated_user(self) -> dict[str, Any]:
        """Get the authenticated user's information.

        Returns:
            User data dictionary

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = await self._request_with_retry("GET", f"{self.base_url}/user")
        result: dict[str, Any] = response.json()
        return result

    async def get_user(self, username: str) -> dict[str, Any]:
        """Get public information about a GitHub user.

        Args:
            username: GitHub username

        Returns:
            User data dictionary including bio, avatar_url, blog, twitter_username,
            company, location, name, public_repos, followers, following, etc.

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = await self._request_with_retry("GET", f"{self.base_url}/users/{username}")
        result: dict[str, Any] = response.json()
        return result

    async def get_user_social_accounts(self, username: str) -> list[dict[str, Any]]:
        """Get social media accounts for a GitHub user.

        Fetches social accounts from GitHub's /users/{username}/social_accounts endpoint,
        which returns accounts for platforms like Mastodon, LinkedIn, and Bluesky.

        Args:
            username: GitHub username

        Returns:
            List of social account dictionaries with 'provider' and 'url' keys.
            Returns empty list if user has no social accounts or if request fails.

        Note:
            This method handles errors gracefully by returning an empty list rather
            than raising exceptions, as social accounts are optional profile data.
        """
        try:
            response = await self._request_with_retry("GET", f"{self.base_url}/users/{username}/social_accounts")
            result: list[dict[str, Any]] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            # 404 means user has no social accounts configured
            if e.response.status_code == 404:
                logger.debug(f"No social accounts found for {username}")
                return []
            # Log other errors but don't fail the request
            logger.warning(f"Failed to fetch social accounts for {username}: {e}")
            return []
        except Exception as e:
            # Handle any other unexpected errors gracefully
            logger.warning(f"Unexpected error fetching social accounts for {username}: {e}")
            return []

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Get public information about a GitHub repository.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name

        Returns:
            Repository data dictionary including stargazers_count, forks_count,
            description, created_at, updated_at, etc.

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = await self._request_with_retry("GET", f"{self.base_url}/repos/{owner}/{repo}")
        result: dict[str, Any] = response.json()
        return result

    async def search_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search for issues/PRs using GitHub search API.

        Args:
            query: GitHub search query (e.g., "is:pr author:username created:>=2024-01-01")
            sort: Sort field (created, updated, comments)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            Search results dictionary with 'total_count' and 'items' keys

        Raises:
            httpx.HTTPStatusError: If the request fails after retries
        """
        params: dict[str, str | int] = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page,
        }

        response = await self._request_with_retry("GET", f"{self.base_url}/search/issues", params=params)
        result: dict[str, Any] = response.json()
        return result

    async def search_all_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100,
        max_results: int | None = None,
        max_concurrent_pages: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for all issues/PRs, handling pagination automatically with concurrent requests.

        Args:
            query: GitHub search query
            sort: Sort field (created, updated, comments)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            max_results: Maximum total results to fetch (None for all)
            max_concurrent_pages: Maximum number of concurrent page fetches (default: 5)

        Returns:
            List of all matching issues/PRs

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        # Fetch first page to determine total count
        logger.debug(f"Fetching first page of search results (query: {query})")
        first_result = await self.search_issues(query, sort, order, per_page, 1)
        total_count = first_result.get("total_count", 0)
        first_items = first_result.get("items", [])

        logger.debug(f"Total results available: {total_count}")

        # Determine how many results we actually need
        target_count = min(total_count, max_results) if max_results else total_count

        # If we got everything in first page, return immediately
        if len(first_items) >= target_count:
            result_items: list[dict[str, Any]] = first_items[:target_count]
            return result_items

        # Calculate how many pages we need
        total_pages = (target_count + per_page - 1) // per_page

        # If only 2 pages, fetch sequentially (not worth the overhead)
        if total_pages <= 2:
            all_items = list(first_items)
            result = await self.search_issues(query, sort, order, per_page, 2)
            all_items.extend(result.get("items", []))
            return_items: list[dict[str, Any]] = all_items[:target_count]
            return return_items

        # Fetch remaining pages with limited concurrency
        logger.debug(f"Fetching pages 2-{total_pages} with max {max_concurrent_pages} concurrent requests")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent_pages)

        async def fetch_page_with_semaphore(page: int) -> dict[str, Any] | None:
            """Fetch a single page with semaphore limiting concurrency."""
            async with semaphore:
                try:
                    return await self.search_issues(query, sort, order, per_page, page)
                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    return None

        tasks = [fetch_page_with_semaphore(page) for page in range(2, total_pages + 1)]

        # Execute all requests with limited concurrency
        remaining_results = await asyncio.gather(*tasks)

        # Combine all results
        all_items = list(first_items)
        page_result: dict[str, Any] | None
        for page_result in remaining_results:
            if page_result is not None:
                all_items.extend(page_result.get("items", []))

        logger.debug(f"Collected {len(all_items)} total items")
        return_items_final: list[dict[str, Any]] = all_items[:target_count]
        return return_items_final

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Rate limit data dictionary

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async with context manager")

        response = await self._client.get(f"{self.base_url}/rate_limit")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_pr_files(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        """Get list of files changed in a pull request.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            number: Pull request number

        Returns:
            List of file data dictionaries including filename, additions, deletions, changes, etc.

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        # GitHub API returns paginated results for PR files (max 3000 files)
        per_page = 100
        page = 1
        all_files: list[dict[str, Any]] = []

        while True:
            response = await self._request_with_retry(
                "GET",
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}/files",
                params={"per_page": per_page, "page": page},
            )
            files: list[dict[str, Any]] = response.json()

            if not files:
                break

            all_files.extend(files)

            # Check if there are more pages
            if len(files) < per_page:
                break

            page += 1

        return all_files

    async def execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against GitHub's GraphQL API.

        Args:
            query: GraphQL query string
            variables: Optional dictionary of GraphQL variables

        Returns:
            GraphQL response data dictionary

        Raises:
            httpx.HTTPStatusError: If the HTTP request fails
            ValueError: If GraphQL response contains errors
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self._request_with_retry("POST", "https://api.github.com/graphql", json=payload)
        result: dict[str, Any] = response.json()

        # Check for GraphQL errors
        if "errors" in result:
            error_messages = [error.get("message", str(error)) for error in result["errors"]]
            raise ValueError(f"GraphQL errors: {'; '.join(error_messages)}")

        return result
