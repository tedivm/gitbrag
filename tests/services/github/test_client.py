"""Tests for GitHub API client."""

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from gitbrag.services.github.client import GitHubAPIClient


@pytest.mark.asyncio
async def test_execute_graphql_success(mock_client: GitHubAPIClient) -> None:
    """Test successful GraphQL query execution."""
    query = "query { viewer { login } }"
    variables = {"var1": "value1"}
    expected_data = {"data": {"viewer": {"login": "testuser"}}}

    with patch.object(mock_client, "_client") as mock_http_client:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_response.raise_for_status = lambda: None
        mock_http_client.request = AsyncMock(return_value=mock_response)

        result = await mock_client.execute_graphql(query=query, variables=variables)

        assert result == expected_data
        mock_http_client.request.assert_called_once_with(
            "POST",
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
        )


@pytest.mark.asyncio
async def test_execute_graphql_without_variables(mock_client: GitHubAPIClient) -> None:
    """Test GraphQL query execution without variables."""
    query = "query { viewer { login } }"
    expected_data = {"data": {"viewer": {"login": "testuser"}}}

    with patch.object(mock_client, "_client") as mock_http_client:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_response.raise_for_status = lambda: None
        mock_http_client.request = AsyncMock(return_value=mock_response)

        result = await mock_client.execute_graphql(query=query)

        assert result == expected_data
        mock_http_client.request.assert_called_once_with(
            "POST",
            "https://api.github.com/graphql",
            json={"query": query},
        )


@pytest.mark.asyncio
async def test_execute_graphql_with_graphql_errors(mock_client: GitHubAPIClient) -> None:
    """Test handling of GraphQL errors in response."""
    query = "query { invalid }"
    error_response = {
        "errors": [
            {"message": "Field 'invalid' doesn't exist on type 'Query'"},
            {"message": "Another error"},
        ]
    }

    with patch.object(mock_client, "_client") as mock_http_client:
        mock_response = AsyncMock()
        mock_response.json = lambda: error_response
        mock_response.raise_for_status = lambda: None
        mock_http_client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError) as exc_info:
            await mock_client.execute_graphql(query=query)

        assert "GraphQL errors" in str(exc_info.value)
        assert "Field 'invalid' doesn't exist" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_graphql_http_error(mock_client: GitHubAPIClient) -> None:
    """Test handling of HTTP errors."""
    query = "query { viewer { login } }"

    with patch.object(mock_client, "_client") as mock_http_client:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Server error", request=AsyncMock(), response=mock_response)
        )
        mock_http_client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.execute_graphql(query=query)


@pytest.mark.asyncio
async def test_get_authenticated_user_success(mock_client: GitHubAPIClient) -> None:
    """Test successful retrieval of authenticated user."""
    expected_data = {"login": "testuser", "id": 12345, "email": "test@example.com"}

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.get_authenticated_user()

        assert result == expected_data
        mock_request.assert_called_once_with("GET", "https://api.github.com/user")


@pytest.mark.asyncio
async def test_get_authenticated_user_http_error(mock_client: GitHubAPIClient) -> None:
    """Test HTTP error when retrieving authenticated user."""
    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_request.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=AsyncMock(), response=AsyncMock(status_code=401)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.get_authenticated_user()


@pytest.mark.asyncio
async def test_get_user_success(mock_client: GitHubAPIClient) -> None:
    """Test successful retrieval of public user information."""
    expected_data = {
        "login": "octocat",
        "id": 583231,
        "bio": "GitHub mascot",
        "company": "GitHub",
        "location": "San Francisco",
        "public_repos": 8,
        "followers": 10000,
        "following": 5,
    }

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.get_user("octocat")

        assert result == expected_data
        mock_request.assert_called_once_with("GET", "https://api.github.com/users/octocat")


@pytest.mark.asyncio
async def test_get_user_not_found(mock_client: GitHubAPIClient) -> None:
    """Test handling of non-existent user."""
    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_request.side_effect = httpx.HTTPStatusError(
            "Not Found", request=AsyncMock(), response=AsyncMock(status_code=404)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.get_user("nonexistentuser12345")


@pytest.mark.asyncio
async def test_get_repository_success(mock_client: GitHubAPIClient) -> None:
    """Test successful retrieval of repository information."""
    expected_data = {
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "description": "My first repository",
        "stargazers_count": 1500,
        "forks_count": 500,
        "language": "Python",
        "created_at": "2011-01-26T19:01:12Z",
    }

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.get_repository("octocat", "Hello-World")

        assert result == expected_data
        mock_request.assert_called_once_with("GET", "https://api.github.com/repos/octocat/Hello-World")


@pytest.mark.asyncio
async def test_get_repository_not_found(mock_client: GitHubAPIClient) -> None:
    """Test handling of non-existent repository."""
    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_request.side_effect = httpx.HTTPStatusError(
            "Not Found", request=AsyncMock(), response=AsyncMock(status_code=404)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.get_repository("octocat", "nonexistent-repo")


@pytest.mark.asyncio
async def test_search_issues_success(mock_client: GitHubAPIClient) -> None:
    """Test successful issue/PR search."""
    expected_data = {
        "total_count": 2,
        "items": [
            {"number": 1, "title": "First PR", "state": "closed"},
            {"number": 2, "title": "Second PR", "state": "open"},
        ],
    }

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.search_issues(
            query="is:pr author:testuser", sort="created", order="desc", per_page=50, page=1
        )

        assert result == expected_data
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/search/issues",
            params={
                "q": "is:pr author:testuser",
                "sort": "created",
                "order": "desc",
                "per_page": 50,
                "page": 1,
            },
        )


@pytest.mark.asyncio
async def test_search_issues_max_per_page(mock_client: GitHubAPIClient) -> None:
    """Test that per_page is capped at 100."""
    expected_data = {"total_count": 250, "items": []}

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.search_issues(query="is:pr", per_page=500)

        assert result == expected_data
        # Verify per_page was capped at 100
        call_args = mock_request.call_args
        assert call_args[1]["params"]["per_page"] == 100


@pytest.mark.asyncio
async def test_search_issues_default_params(mock_client: GitHubAPIClient) -> None:
    """Test search_issues with default parameters."""
    expected_data = {"total_count": 0, "items": []}

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_data
        mock_request.return_value = mock_response

        result = await mock_client.search_issues(query="is:pr")

        assert result == expected_data
        call_args = mock_request.call_args
        assert call_args[1]["params"]["sort"] == "created"
        assert call_args[1]["params"]["order"] == "desc"
        assert call_args[1]["params"]["per_page"] == 100
        assert call_args[1]["params"]["page"] == 1


@pytest.mark.asyncio
async def test_execute_graphql_rate_limit_with_retry(mock_client: GitHubAPIClient) -> None:
    """Test rate limit handling with automatic retry."""
    query = "query { viewer { login } }"
    expected_data = {"data": {"viewer": {"login": "testuser"}}}

    with (
        patch.object(mock_client, "_client") as mock_http_client,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        # First call: rate limit error
        mock_rate_limit_response = AsyncMock()
        mock_rate_limit_response.status_code = 429
        mock_rate_limit_response.headers = {"X-RateLimit-Reset": "1234567890"}
        rate_limit_error = httpx.HTTPStatusError("Rate limit", request=AsyncMock(), response=mock_rate_limit_response)

        # Second call: success
        mock_success_response = AsyncMock()
        mock_success_response.json = lambda: expected_data
        mock_success_response.raise_for_status = lambda: None

        # Set up mock to fail once, then succeed
        mock_http_client.request = AsyncMock(
            side_effect=[
                mock_rate_limit_response,
                mock_success_response,
            ]
        )
        mock_rate_limit_response.raise_for_status = lambda: (_ for _ in ()).throw(rate_limit_error)

        with patch("time.time", return_value=1234567850):  # 40 seconds before reset
            result = await mock_client.execute_graphql(query=query)

        assert result == expected_data
        assert mock_http_client.request.call_count == 2
        mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_execute_graphql_rate_limit_max_retries_exceeded(mock_client: GitHubAPIClient) -> None:
    """Test that rate limit errors are raised after max retries."""
    query = "query { viewer { login } }"

    with (
        patch.object(mock_client, "_client") as mock_http_client,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.headers = {"X-RateLimit-Reset": "1234567890"}
        rate_limit_error = httpx.HTTPStatusError("Rate limit", request=AsyncMock(), response=mock_response)
        mock_response.raise_for_status = lambda: (_ for _ in ()).throw(rate_limit_error)
        mock_http_client.request = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.execute_graphql(query=query)

        # Should try initial + 3 retries (default max_retries in _request_with_retry) = 4 times
        assert mock_http_client.request.call_count == 4


@pytest.mark.asyncio
async def test_execute_graphql_not_initialized(mock_client: GitHubAPIClient) -> None:
    """Test that executing GraphQL without initializing client raises error."""
    query = "query { viewer { login } }"

    # Client is not initialized (no async context manager)
    with pytest.raises(RuntimeError) as exc_info:
        await mock_client.execute_graphql(query=query)

    assert "Client not initialized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_all_issues_single_page(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues when all results fit in first page."""
    expected_items = [
        {"number": 1, "title": "First PR"},
        {"number": 2, "title": "Second PR"},
    ]

    with patch.object(mock_client, "search_issues") as mock_search:
        mock_search.return_value = {"total_count": 2, "items": expected_items}

        result = await mock_client.search_all_issues(query="is:pr")

        assert result == expected_items
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_all_issues_two_pages(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues with 2 pages (sequential fetch)."""
    page1_items = [{"number": 1}, {"number": 2}]
    page2_items = [{"number": 3}, {"number": 4}]

    async def mock_search_side_effect(query: str, sort: str, order: str, per_page: int, page: int) -> dict[str, Any]:
        if page == 1:
            return {"total_count": 4, "items": page1_items}
        elif page == 2:
            return {"total_count": 4, "items": page2_items}
        return {"total_count": 0, "items": []}

    with patch.object(mock_client, "search_issues", side_effect=mock_search_side_effect):
        result = await mock_client.search_all_issues(query="is:pr", per_page=2)

        assert len(result) == 4
        assert result == page1_items + page2_items


@pytest.mark.asyncio
async def test_search_all_issues_multiple_pages_concurrent(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues with multiple pages (concurrent fetch)."""
    items_per_page = 2
    total_items = 6
    pages = {
        1: [{"number": 1}, {"number": 2}],
        2: [{"number": 3}, {"number": 4}],
        3: [{"number": 5}, {"number": 6}],
    }

    async def mock_search_side_effect(query: str, sort: str, order: str, per_page: int, page: int) -> dict[str, Any]:
        return {"total_count": total_items, "items": pages.get(page, [])}

    with patch.object(mock_client, "search_issues", side_effect=mock_search_side_effect):
        result = await mock_client.search_all_issues(query="is:pr", per_page=items_per_page)

        assert len(result) == total_items
        # Verify all items are present
        numbers = [item["number"] for item in result]
        assert sorted(numbers) == [1, 2, 3, 4, 5, 6]


@pytest.mark.asyncio
async def test_search_all_issues_with_max_results(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues with max_results limit."""
    first_page_items = [{"number": i} for i in range(1, 101)]

    with patch.object(mock_client, "search_issues") as mock_search:
        mock_search.return_value = {"total_count": 500, "items": first_page_items}

        result = await mock_client.search_all_issues(query="is:pr", per_page=100, max_results=50)

        # Should only return first 50 items
        assert len(result) == 50
        assert result == first_page_items[:50]
        # Should only call once since first page has more than max_results
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_all_issues_empty_results(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues with no results."""
    with patch.object(mock_client, "search_issues") as mock_search:
        mock_search.return_value = {"total_count": 0, "items": []}

        result = await mock_client.search_all_issues(query="is:pr author:nonexistent")

        assert result == []
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_all_issues_concurrent_limit(mock_client: GitHubAPIClient) -> None:
    """Test search_all_issues respects max_concurrent_pages."""
    total_pages = 10
    items_per_page = 10

    async def mock_search_side_effect(query: str, sort: str, order: str, per_page: int, page: int) -> dict[str, Any]:
        return {"total_count": 100, "items": [{"number": page * 10 + i} for i in range(10)]}

    with patch.object(mock_client, "search_issues", side_effect=mock_search_side_effect):
        # Use max_concurrent_pages=2 to test semaphore limiting
        result = await mock_client.search_all_issues(query="is:pr", per_page=items_per_page, max_concurrent_pages=2)

        assert len(result) == 100
        # Verify the search_issues was called correct number of times
        assert mock_client.search_issues.call_count == total_pages


@pytest.mark.asyncio
async def test_get_user_social_accounts_success(mock_client: GitHubAPIClient) -> None:
    """Test successful retrieval of user social accounts."""
    username = "tedivm"
    expected_accounts = [
        {"provider": "mastodon", "url": "https://hachyderm.io/@tedivm"},
        {"provider": "linkedin", "url": "https://www.linkedin.com/in/roberthafner/"},
        {"provider": "bluesky", "url": "https://bsky.app/profile/tedivm.com"},
    ]

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: expected_accounts
        mock_request.return_value = mock_response

        result = await mock_client.get_user_social_accounts(username)

        assert result == expected_accounts
        mock_request.assert_called_once_with("GET", f"https://api.github.com/users/{username}/social_accounts")


@pytest.mark.asyncio
async def test_get_user_social_accounts_empty(mock_client: GitHubAPIClient) -> None:
    """Test handling of user with no social accounts."""
    username = "noaccounts"

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.json = lambda: []
        mock_request.return_value = mock_response

        result = await mock_client.get_user_social_accounts(username)

        assert result == []


@pytest.mark.asyncio
async def test_get_user_social_accounts_404(mock_client: GitHubAPIClient) -> None:
    """Test handling of 404 response (user has no social accounts configured)."""
    username = "user404"

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_request.side_effect = httpx.HTTPStatusError("Not found", request=AsyncMock(), response=mock_response)

        result = await mock_client.get_user_social_accounts(username)

        # Should return empty list instead of raising exception
        assert result == []


@pytest.mark.asyncio
async def test_get_user_social_accounts_other_http_error(mock_client: GitHubAPIClient) -> None:
    """Test handling of non-404 HTTP errors."""
    username = "erroruser"

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_request.side_effect = httpx.HTTPStatusError("Server error", request=AsyncMock(), response=mock_response)

        result = await mock_client.get_user_social_accounts(username)

        # Should return empty list and log warning instead of raising exception
        assert result == []


@pytest.mark.asyncio
async def test_get_user_social_accounts_unexpected_error(mock_client: GitHubAPIClient) -> None:
    """Test handling of unexpected errors."""
    username = "erroruser"

    with patch.object(mock_client, "_request_with_retry") as mock_request:
        mock_request.side_effect = Exception("Unexpected error")

        result = await mock_client.get_user_social_accounts(username)

        # Should return empty list and log warning instead of raising exception
        assert result == []
