"""Tests for FastAPI web application."""

import pytest

from gitbrag.settings import settings
from gitbrag.www import app


def test_app_exists():
    """Test that the FastAPI app is properly instantiated."""
    assert app is not None
    assert hasattr(app, "router")


def test_static_files_mounted():
    """Test that static files are properly mounted."""
    routes = [route.path for route in app.routes]
    assert "/static" in routes or any("/static" in route for route in routes)


def test_home_page(fastapi_client):
    """Test that home page is accessible."""
    response = fastapi_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert b"git brag" in response.content
    assert b"Login with GitHub" in response.content


@pytest.mark.skipif(
    not settings.github_app_client_id or not settings.github_app_client_secret,
    reason="OAuth credentials not configured (GITHUB_APP_CLIENT_ID and GITHUB_APP_CLIENT_SECRET required)",
)
def test_login_route_exists(fastapi_client):
    """Test that login route redirects to GitHub."""
    response = fastapi_client.get("/auth/login", follow_redirects=False)
    # Should redirect to GitHub OAuth
    assert response.status_code in (302, 307)
    assert "github.com" in response.headers.get("location", "")


def test_logout_route(fastapi_client):
    """Test that logout route redirects to home."""
    response = fastapi_client.get("/auth/logout", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "/"


def test_error_404(fastapi_client):
    """Test 404 error handling."""
    response = fastapi_client.get("/nonexistent-page")
    assert response.status_code == 404
    assert b"Not Found" in response.content


def test_openapi_schema(fastapi_client):
    """Test that OpenAPI schema is accessible."""
    response = fastapi_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


def test_static_route_exists():
    """Test that static route is configured."""
    routes = {route.path: route for route in app.routes}
    # Static files might be mounted at /static or have a prefix
    has_static = any("/static" in path for path in routes.keys())
    assert has_static, "Static files route should be configured"


def test_lifespan_configured():
    """Test that lifespan context manager is configured."""
    # Check that the app has a lifespan handler
    assert app.router.lifespan_context is not None, "Should have lifespan context configured"


def test_app_can_start(fastapi_client):
    """Test that the app can start successfully."""
    # Making any request will trigger startup event
    response = fastapi_client.get("/docs")
    assert response.status_code == 200


def test_basic_health(fastapi_client):
    """Test basic application health by accessing root."""
    response = fastapi_client.get("/")
    assert response.status_code in [200, 307], "App should respond to requests"
