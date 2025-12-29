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
    location = response.headers.get("location", "")
    assert location.startswith("https://github.com/") or location.startswith("http://github.com/")


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


def test_basic_meta_tags(fastapi_client):
    """Test that basic meta tags are present in HTML."""
    response = fastapi_client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert '<meta name="description"' in content
    assert '<meta name="author"' in content
    assert '<meta name="keywords"' in content


def test_open_graph_metadata(fastapi_client):
    """Test that Open Graph metadata is present in HTML."""
    response = fastapi_client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert '<meta property="og:type"' in content
    assert '<meta property="og:site_name"' in content
    assert '<meta property="og:title"' in content
    assert '<meta property="og:description"' in content
    assert '<meta property="og:image"' in content


def test_twitter_card_metadata(fastapi_client):
    """Test that Twitter Card metadata is present in HTML."""
    response = fastapi_client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert '<meta name="twitter:card" content="summary_large_image"' in content
    assert '<meta name="twitter:title"' in content
    assert '<meta name="twitter:description"' in content
    assert '<meta name="twitter:image"' in content


def test_plausible_script_not_injected_by_default(fastapi_client):
    """Test that Plausible script is not injected when not configured."""
    response = fastapi_client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    # Should not contain Plausible script when disabled
    assert "plausible.io" not in content.lower() or settings.enable_plausible


def test_plausible_script_requires_both_settings(fastapi_client, monkeypatch):
    """Test that Plausible script requires both enable_plausible and plausible_script_hash."""
    # This test verifies the logic in the template
    # When only enable_plausible is True but hash is missing, script should not be injected
    response = fastapi_client.get("/")
    content = response.content.decode()

    # If Plausible is enabled and hash is set, script should be present
    if settings.enable_plausible and settings.plausible_script_hash:
        assert "plausible.io" in content.lower()
    else:
        # Otherwise script should not be present
        assert "plausible.io" not in content.lower()


def test_username_redirect_to_lowercase(fastapi_client):
    """Test that uppercase usernames redirect to lowercase URLs with 301 status."""
    # Test uppercase username redirects
    response = fastapi_client.get("/user/github/TEDIVM", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers.get("location") == "/user/github/tedivm"

    # Test mixed case redirects
    response = fastapi_client.get("/user/github/TedIVM", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers.get("location") == "/user/github/tedivm"

    # Test query parameters are preserved
    response = fastapi_client.get("/user/github/TEDIVM?period=2_years&force=true", follow_redirects=False)
    assert response.status_code == 301
    location = response.headers.get("location")
    assert location.startswith("/user/github/tedivm?")
    assert "period=2_years" in location
    assert "force=true" in location


def test_empty_state_encouraging_message():
    """Test that user_report.html template contains encouraging empty state message."""
    # Read template and verify it contains the encouraging message
    import os

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gitbrag", "templates", "user_report.html")
    with open(template_path) as f:
        content = f.read()

    # Verify the encouraging message is in the template
    assert "Every open source journey starts somewhere" in content
    assert "next contribution" in content
    assert "waiting" in content
    assert "🚀" in content  # Rocket emoji


def test_company_name_with_at_symbol_becomes_link():
    """Test that company names starting with @ are converted to GitHub profile links."""
    import os

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gitbrag", "templates", "user_report.html")
    with open(template_path) as f:
        content = f.read()

    # Verify the template has logic to convert @company to links
    assert "user_profile.company.startswith('@')" in content
    assert 'href="https://github.com/{{ user_profile.company[1:]' in content
    assert 'target="_blank"' in content
