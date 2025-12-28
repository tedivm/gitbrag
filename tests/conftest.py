import os

# Set required environment variables for testing BEFORE any gitbrag imports
# This must happen before settings are loaded
if "SESSION_SECRET_KEY" not in os.environ:
    os.environ["SESSION_SECRET_KEY"] = "test-secret-key-for-testing-purposes-only-min-32-chars"

# Enable caching for tests
if "CACHE_ENABLED" not in os.environ:
    os.environ["CACHE_ENABLED"] = "true"

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import SecretStr

from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.www import app


@pytest_asyncio.fixture
async def fastapi_client():
    """Fixture to create a FastAPI test client."""
    client = TestClient(app)
    yield client


@pytest.fixture
def mock_client() -> GitHubAPIClient:
    """Create a test GitHub API client for mocking."""
    return GitHubAPIClient(token=SecretStr("test_token"))
