"""Authentication dependencies for FastAPI routes.

This module provides FastAPI dependencies for handling authentication
and creating authenticated GitHub clients.
"""

from logging import getLogger

from fastapi import HTTPException, Request, status

from gitbrag.services.github.client import GitHubAPIClient
from gitbrag.services.session import get_decrypted_token, is_authenticated, set_session_data
from gitbrag.settings import settings

logger = getLogger(__name__)


async def get_authenticated_github_client(
    request: Request,
) -> GitHubAPIClient:
    """Get authenticated GitHub client from session.

    Args:
        request: FastAPI request object

    Returns:
        Authenticated GitHubAPIClient instance

    Raises:
        HTTPException: 401 if not authenticated or token invalid
    """
    # Check if user is authenticated
    if not is_authenticated(request):
        logger.warning("Unauthenticated access attempt to protected route")
        # Store original URL for post-login redirect
        set_session_data(request, "redirect_after_login", str(request.url))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Get decrypted token from session
    token = get_decrypted_token(request, settings)

    if token is None:
        logger.error("Failed to decrypt token from session")
        # Clear invalid session
        set_session_data(request, "oauth_token", None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session - please log in again",
        )

    # Create and return authenticated client
    try:
        client = GitHubAPIClient(token=token)
        return client
    except Exception as e:
        logger.exception(f"Failed to create GitHub client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create GitHub client",
        )


async def get_optional_github_client(
    request: Request,
) -> GitHubAPIClient | None:
    """Get authenticated GitHub client if available, None otherwise.

    This is for routes that work with or without authentication.

    Args:
        request: FastAPI request object

    Returns:
        Authenticated GitHubAPIClient instance if authenticated, None otherwise
    """
    if not is_authenticated(request):
        return None

    token = get_decrypted_token(request, settings)

    if token is None:
        logger.warning("Failed to decrypt token for optional client")
        # Clear invalid session
        set_session_data(request, "oauth_token", None)
        return None

    try:
        client = GitHubAPIClient(token=token)
        return client
    except Exception as e:
        logger.exception(f"Failed to create optional GitHub client: {e}")
        return None
