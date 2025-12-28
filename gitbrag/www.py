import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from logging import getLogger
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import SecretStr
from starlette.responses import Response

from gitbrag.services.auth import get_optional_github_client
from gitbrag.services.cache import configure_caches
from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.services.github.web_oauth import WebOAuthFlow
from gitbrag.services.reports import (
    calculate_date_range,
    get_or_fetch_user_profile,
    get_or_generate_report,
    normalize_period,
)
from gitbrag.services.session import (
    add_session_middleware,
    clear_session,
    get_session,
    is_authenticated,
    set_session_data,
    store_encrypted_token,
)
from gitbrag.settings import settings

logger = getLogger(__name__)

# Validate required web settings
if not settings.session_secret_key:
    raise ValueError(
        "SESSION_SECRET_KEY environment variable is required for web interface. "
        "Generate a secure random key with at least 32 characters. "
        "Example: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan events."""
    # Startup: Initialize caches
    configure_caches()
    yield
    # Shutdown: cleanup would go here if needed


app = FastAPI(lifespan=lifespan)

# Add session middleware
add_session_middleware(app, settings)

static_file_path = os.path.dirname(os.path.realpath(__file__)) + "/static"
app.mount("/static", StaticFiles(directory=static_file_path), name="static")

# Setup Jinja2 templates
templates_path = os.path.dirname(os.path.realpath(__file__)) + "/templates"
templates = Jinja2Templates(directory=templates_path)


# Exception Handlers


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> Response:
    """Handle 404 Not Found errors.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        Rendered error template
    """
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "error_code": 404,
            "error_title": "Not Found",
            "error_message": "The page you're looking for doesn't exist.",
            "show_login": False,
        },
        status_code=404,
    )


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException) -> Response:
    """Handle 401 Unauthorized errors.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        Rendered error template
    """
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "error_code": 401,
            "error_title": "Authentication Required",
            "error_message": exc.detail if hasattr(exc, "detail") else "You need to log in to access this page.",
            "show_login": True,
        },
        status_code=401,
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: HTTPException) -> Response:
    """Handle 429 Rate Limit errors.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        Rendered error template
    """
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "error_code": 429,
            "error_title": "Rate Limited",
            "error_message": "You've made too many requests. Please try again later.",
            "show_login": False,
        },
        status_code=429,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> Response:
    """Handle 500 Internal Server errors.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        Rendered error template
    """
    logger.exception("Internal server error", exc_info=exc)
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "error_code": 500,
            "error_title": "Internal Server Error",
            "error_message": "Something went wrong on our end. Please try again later.",
            "show_login": False,
        },
        status_code=500,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> Response:
    """Handle request validation errors.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        Rendered error template
    """
    logger.warning(f"Validation error: {exc.errors()}")
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "error_code": 400,
            "error_title": "Bad Request",
            "error_message": "Invalid request parameters.",
            "show_login": False,
        },
        status_code=400,
    )


# Routes


@app.get("/", include_in_schema=False)
async def root(
    request: Request,
    github_client: GitHubAPIClient | None = Depends(get_optional_github_client),
) -> Response:
    """Home page with login option.

    Args:
        request: FastAPI request object
        github_client: Optional authenticated GitHub client

    Returns:
        Rendered home page template
    """
    authenticated = is_authenticated(request)
    username = None

    # Get username if authenticated
    if github_client:
        try:
            async with github_client:
                user_info = await github_client.get_authenticated_user()
                username = user_info.get("login")
        except Exception as e:
            logger.warning(f"Failed to get authenticated user info: {e}")

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "authenticated": authenticated,
            "username": username,
            "example_username": settings.example_username,
        },
    )


# OAuth Routes


@app.get("/auth/login")
async def login(request: Request, return_to: str = Query(default="/")) -> RedirectResponse:
    """Initiate GitHub OAuth flow.

    Args:
        request: FastAPI request object
        return_to: URL to redirect to after successful authentication

    Returns:
        Redirect to GitHub authorization page
    """
    # Validate GitHub OAuth configuration
    if not settings.github_app_client_id or not settings.github_app_client_secret:
        logger.error("GitHub OAuth not configured: missing client_id or client_secret")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth not configured. Please set GITHUB_APP_CLIENT_ID and GITHUB_APP_CLIENT_SECRET.",
        )

    # Create OAuth flow
    oauth = WebOAuthFlow(
        client_id=settings.github_app_client_id,
        client_secret=settings.github_app_client_secret,
        callback_url=settings.oauth_callback_url,
    )

    # Generate state and store in session for CSRF protection
    state = oauth.generate_state()
    set_session_data(request, "oauth_state", state)
    set_session_data(request, "return_to", return_to)

    # Generate authorization URL with minimal scopes
    scopes = settings.oauth_scopes.split()
    auth_url = oauth.get_authorization_url(state=state, scopes=scopes)

    logger.info(f"Redirecting to GitHub OAuth with scopes: {', '.join(scopes)}")
    return RedirectResponse(auth_url, status_code=status.HTTP_302_FOUND)


@app.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: str | None = Query(default=None, description="Error from GitHub OAuth"),
) -> RedirectResponse:
    """Handle OAuth callback from GitHub.

    Args:
        request: FastAPI request object
        code: Authorization code from GitHub
        state: State parameter for CSRF validation
        error: Optional error from GitHub

    Returns:
        Redirect to originally requested page or home

    Raises:
        HTTPException: If OAuth flow fails
    """
    # Check for OAuth denial/error
    if error:
        logger.warning(f"OAuth callback error: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth authorization failed: {error}",
        )

    # Validate state parameter (CSRF protection)
    session = get_session(request)
    stored_state = session.get("oauth_state")

    if not stored_state or stored_state != state:
        logger.error("Invalid OAuth state parameter - possible CSRF attack")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Please try logging in again.",
        )

    # Create OAuth flow
    if not settings.github_app_client_id or not settings.github_app_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth not configured",
        )
    oauth = WebOAuthFlow(
        client_id=settings.github_app_client_id,
        client_secret=settings.github_app_client_secret,
        callback_url=settings.oauth_callback_url,
    )

    # Exchange code for token
    try:
        token = await oauth.exchange_code_for_token(code)
    except Exception as e:
        logger.exception(f"Failed to exchange OAuth code for token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth authentication. Please try again.",
        )

    # Encrypt and store token in session
    store_encrypted_token(request, token, settings)

    # Clear OAuth state from session
    set_session_data(request, "oauth_state", None)

    # Redirect to originally requested page or home
    return_to = session.get("return_to", "/")
    set_session_data(request, "return_to", None)

    logger.info("OAuth authentication successful")
    return RedirectResponse(return_to, status_code=status.HTTP_302_FOUND)


@app.get("/auth/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out user by clearing session.

    Args:
        request: FastAPI request object

    Returns:
        Redirect to home page
    """
    clear_session(request)
    logger.info("User logged out")
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


# Report Routes


@app.get("/user/github/{username}")
async def user_report(
    request: Request,
    username: str,
    period: str = Query(default="1_year", description="Time period for report"),
    force: bool = Query(default=False, description="Force regenerate report"),
    github_client: GitHubAPIClient | None = Depends(get_optional_github_client),
) -> Response:
    """Display contribution report for a GitHub user.

    Args:
        request: FastAPI request object
        username: GitHub username
        period: Time period (1_year, 2_years, all_time)
        force: Force regenerate regardless of cache
        github_client: Optional authenticated GitHub client

    Returns:
        Rendered user report template
    """
    # Normalize period parameter
    period = normalize_period(period)
    logger.info(f"User report for {username}, period={period}")

    # Prepare token for API calls
    token_str = github_client.token if github_client else None

    # Always show star increase data when available
    show_star_increase = True

    # Run all GitHub API calls in parallel for better performance
    report_data = None
    metadata = None
    user_profile = None

    if token_str:
        # Create clients for parallel operations
        auth_client = GitHubAPIClient(token=SecretStr(token_str))
        report_client = GitHubAPIClient(token=SecretStr(token_str))

        async def get_auth_user() -> str | None:
            try:
                async with auth_client:
                    user_info = await auth_client.get_authenticated_user()
                    return user_info.get("login")
            except Exception as e:
                logger.warning(f"Failed to get authenticated user info: {e}")
                return None

        async def get_report() -> tuple[dict[str, Any], dict[str, Any]]:
            return await get_or_generate_report(
                github_client=report_client,
                username=username,
                period=period,
                show_star_increase=show_star_increase,
                force_refresh=force,
                stale_age=settings.report_cache_stale_age,
                authenticated_user=None,  # Will be updated after parallel calls
            )

        # Execute API operations in parallel
        results = await asyncio.gather(
            get_auth_user(),
            get_report(),
            return_exceptions=False,
        )

        _ = results[0]  # authenticated_user - fetched to verify token but not used in template
        report_data, metadata = results[1]

        # Fetch profile using caching function (pass token, not client)
        user_profile = await get_or_fetch_user_profile(username, token_str)
    else:
        # No token available, just get the report without authentication
        report_data, metadata = await get_or_generate_report(
            github_client=None,
            username=username,
            period=period,
            show_star_increase=show_star_increase,
            force_refresh=force,
            stale_age=settings.report_cache_stale_age,
            authenticated_user=None,
        )

        # Try to get profile from cache (no token means unauthenticated)
        user_profile = await get_or_fetch_user_profile(username, token=None)

    # If no data available and not authenticated, prompt login
    if not report_data:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error_code": 401,
                "error_title": "GitHub Login Required",
                "error_message": f"To view the contribution report for {username}, we need to access the GitHub API to collect the necessary data. No cached report is currently available. Please login with your GitHub account to generate this report.",
                "show_login": True,
            },
            status_code=401,
        )

    # Calculate cache age and status
    cache_info = None
    if metadata:
        cache_age_seconds = datetime.now().timestamp() - metadata["created_at"]
        is_stale = cache_age_seconds >= settings.report_cache_stale_age

        # Format cache age
        if cache_age_seconds < 60:
            cache_age_str = f"{int(cache_age_seconds)} seconds ago"
        elif cache_age_seconds < 3600:
            cache_age_str = f"{int(cache_age_seconds / 60)} minutes ago"
        elif cache_age_seconds < 86400:
            cache_age_str = f"{int(cache_age_seconds / 3600)} hours ago"
        else:
            cache_age_str = f"{int(cache_age_seconds / 86400)} days ago"

        cache_info = {
            "age": cache_age_str,
            "is_stale": is_stale,
        }

    # Calculate date range for display
    since, until = calculate_date_range(period)

    # Prepare template context
    context = {
        "request": request,
        "username": username,
        "period": period,
        "since_date": since.strftime("%Y-%m-%d"),
        "until_date": until.strftime("%Y-%m-%d"),
        "total_prs": report_data["total_prs"],
        "merged_count": report_data["merged_count"],
        "open_count": report_data["open_count"],
        "closed_count": report_data["closed_count"],
        "repo_count": report_data["repo_count"],
        "total_star_increase": report_data.get("total_star_increase"),
        "repositories": report_data["repositories"],
        "repo_descriptions": report_data.get("repo_descriptions", {}),
        "cache_info": cache_info,
        "authenticated": token_str is not None,
        "user_profile": user_profile,
    }

    return templates.TemplateResponse(
        request=request,
        name="user_report.html",
        context=context,
    )
