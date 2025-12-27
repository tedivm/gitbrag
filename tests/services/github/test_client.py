"""Tests for GitHub API client."""

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
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await mock_client.execute_graphql(query=query, variables=variables)

        assert result == expected_data
        mock_http_client.post.assert_called_once_with(
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
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await mock_client.execute_graphql(query=query)

        assert result == expected_data
        mock_http_client.post.assert_called_once_with(
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
        mock_http_client.post = AsyncMock(return_value=mock_response)

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
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.execute_graphql(query=query)


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
        mock_http_client.post = AsyncMock(
            side_effect=[
                mock_rate_limit_response,
                mock_success_response,
            ]
        )
        mock_rate_limit_response.raise_for_status = lambda: (_ for _ in ()).throw(rate_limit_error)

        with patch("time.time", return_value=1234567850):  # 40 seconds before reset
            result = await mock_client.execute_graphql(query=query)

        assert result == expected_data
        assert mock_http_client.post.call_count == 2
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
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.execute_graphql(query=query, max_retries=2)

        # Should try initial + 2 retries = 3 times
        assert mock_http_client.post.call_count == 3


@pytest.mark.asyncio
async def test_execute_graphql_not_initialized(mock_client: GitHubAPIClient) -> None:
    """Test that executing GraphQL without initializing client raises error."""
    query = "query { viewer { login } }"

    # Client is not initialized (no async context manager)
    with pytest.raises(RuntimeError) as exc_info:
        await mock_client.execute_graphql(query=query)

    assert "Client not initialized" in str(exc_info.value)
