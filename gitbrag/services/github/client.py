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
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()

    async def get_authenticated_user(self) -> dict[str, Any]:
        """Get the authenticated user's information.

        Returns:
            User data dictionary

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async with context manager")

        response = await self._client.get(f"{self.base_url}/user")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def search_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100,
        page: int = 1,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Search for issues/PRs using GitHub search API.

        Args:
            query: GitHub search query (e.g., "is:pr author:username created:>=2024-01-01")
            sort: Sort field (created, updated, comments)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            page: Page number
            retry_count: Current retry attempt (internal use)
            max_retries: Maximum number of retries for rate limiting

        Returns:
            Search results dictionary with 'total_count' and 'items' keys

        Raises:
            httpx.HTTPStatusError: If the request fails after retries
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async with context manager")

        params: dict[str, str | int] = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page,
        }

        try:
            response = await self._client.get(f"{self.base_url}/search/issues", params=params)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            # Handle rate limiting (403 or 429)
            if e.response.status_code in (403, 429) and retry_count < max_retries:
                # Check rate limit headers or status code
                # 429 is explicit rate limit, 403 on search API is often rate limiting
                remaining = e.response.headers.get("X-RateLimit-Remaining", "")
                is_rate_limit = e.response.status_code == 429 or remaining == "0"

                if is_rate_limit:
                    # Check if we have a reset time
                    reset_time = e.response.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        # Wait until reset time (but cap at 60 seconds)
                        import time

                        wait_time = min(int(reset_time) - int(time.time()), 60)
                        wait_time = max(wait_time, 1)  # At least 1 second
                    else:
                        # Exponential backoff: 2^retry_count seconds
                        wait_time = 2**retry_count

                    logger.warning(
                        f"Rate limit hit on search API (attempt {retry_count + 1}/{max_retries}). "
                        f"Waiting {wait_time} seconds before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    return await self.search_issues(query, sort, order, per_page, page, retry_count + 1, max_retries)
            # Re-raise if not rate limit or max retries exceeded
            raise

    async def search_all_issues(
        self,
        query: str,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 100,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search for all issues/PRs, handling pagination automatically with concurrent requests.

        Args:
            query: GitHub search query
            sort: Sort field (created, updated, comments)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            max_results: Maximum total results to fetch (None for all)

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

        # Fetch remaining pages concurrently (pages 2 through total_pages)
        logger.debug(f"Fetching pages 2-{total_pages} concurrently")
        tasks = [self.search_issues(query, sort, order, per_page, page) for page in range(2, total_pages + 1)]

        # Execute all requests concurrently
        remaining_results: list[dict[str, Any] | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all results
        all_items = list(first_items)
        for result in remaining_results:  # type: ignore[assignment]
            if isinstance(result, BaseException):
                logger.error(f"Error fetching page: {result}")
                continue
            # At this point, result is dict[str, Any]
            all_items.extend(result.get("items", []))

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
