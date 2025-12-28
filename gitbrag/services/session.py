"""Session management for web interface.

This module provides session middleware configuration and helper functions
for managing user sessions with Redis backend.
"""

from typing import Any

from fastapi import FastAPI, Request
from pydantic import SecretStr
from starlette.middleware.sessions import SessionMiddleware

from gitbrag.conf.settings import Settings
from gitbrag.services.encryption import decrypt_token, encrypt_token


def add_session_middleware(app: FastAPI, settings: Settings) -> None:
    """Add session middleware to FastAPI app.

    Args:
        app: FastAPI application instance
        settings: Application settings

    Raises:
        ValueError: If session_secret_key is not configured
    """
    if not settings.session_secret_key:
        raise ValueError("session_secret_key is required for session middleware")

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key.get_secret_value(),
        max_age=settings.session_max_age,
        https_only=settings.require_https,
        same_site="lax",
    )


def get_session(request: Request) -> dict[str, Any]:
    """Get session data from request.

    Args:
        request: FastAPI request object

    Returns:
        Session dictionary (may be empty for new sessions)
    """
    return request.session if hasattr(request, "session") else {}


def set_session_data(request: Request, key: str, value: Any) -> None:
    """Store data in session.

    Args:
        request: FastAPI request object
        key: Session key
        value: Value to store
    """
    if hasattr(request, "session"):
        request.session[key] = value


def clear_session(request: Request) -> None:
    """Clear all session data.

    Args:
        request: FastAPI request object
    """
    if hasattr(request, "session"):
        request.session.clear()


def store_encrypted_token(request: Request, token: SecretStr | str, settings: Settings) -> None:
    """Encrypt and store OAuth token in session.

    Args:
        request: FastAPI request object
        token: OAuth access token
        settings: Application settings with encryption key

    Raises:
        ValueError: If session_secret_key is not configured
    """
    if not settings.session_secret_key:
        raise ValueError("session_secret_key is required for token encryption")

    encrypted = encrypt_token(token, settings.session_secret_key)
    set_session_data(request, "access_token", encrypted)
    set_session_data(request, "authenticated", True)


def get_decrypted_token(request: Request, settings: Settings) -> SecretStr | None:
    """Retrieve and decrypt OAuth token from session.

    Args:
        request: FastAPI request object
        settings: Application settings with encryption key

    Returns:
        Decrypted token as SecretStr, or None if not found or decryption fails

    Raises:
        ValueError: If session_secret_key is not configured
    """
    if not settings.session_secret_key:
        raise ValueError("session_secret_key is required for token decryption")

    session = get_session(request)
    encrypted_token = session.get("access_token")

    if not encrypted_token:
        return None

    return decrypt_token(encrypted_token, settings.session_secret_key)


def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated.

    Args:
        request: FastAPI request object

    Returns:
        True if user has valid session, False otherwise
    """
    session = get_session(request)
    return session.get("authenticated", False) is True
