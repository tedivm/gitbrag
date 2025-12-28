"""Tests for session management."""

from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from gitbrag.conf.settings import Settings
from gitbrag.services.session import (
    clear_session,
    get_decrypted_token,
    get_session,
    is_authenticated,
    set_session_data,
    store_encrypted_token,
)


@pytest.fixture
def mock_request():
    """Create a mock request with session."""
    request = MagicMock()
    request.session = {}
    return request


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Settings(
        session_secret_key=SecretStr("test-secret-key-for-testing"),
        session_max_age=3600,
    )


def test_get_session_with_session(mock_request):
    """Test getting session data when session exists."""
    mock_request.session = {"key": "value"}

    result = get_session(mock_request)

    assert result == {"key": "value"}


def test_get_session_without_session():
    """Test getting session data when session doesn't exist."""
    request = MagicMock(spec=[])  # No session attribute

    result = get_session(request)

    assert result == {}


def test_set_session_data(mock_request):
    """Test setting session data."""
    set_session_data(mock_request, "test_key", "test_value")

    assert mock_request.session["test_key"] == "test_value"


def test_set_session_data_without_session():
    """Test setting session data when session doesn't exist."""
    request = MagicMock(spec=[])

    # Should not raise error
    set_session_data(request, "key", "value")


def test_clear_session(mock_request):
    """Test clearing session data."""
    mock_request.session = {"key1": "value1", "key2": "value2"}

    clear_session(mock_request)

    # Check that session was cleared
    assert len(mock_request.session) == 0


def test_clear_session_without_session():
    """Test clearing session when session doesn't exist."""
    request = MagicMock(spec=[])

    # Should not raise error
    clear_session(request)


def test_store_encrypted_token(mock_request, mock_settings):
    """Test storing encrypted token in session."""
    token = SecretStr("my-oauth-token")

    store_encrypted_token(mock_request, token, mock_settings)

    # Check that access_token was set (encrypted)
    assert "access_token" in mock_request.session
    assert mock_request.session["access_token"] != token.get_secret_value()
    assert mock_request.session["authenticated"] is True


def test_store_encrypted_token_plain_string(mock_request, mock_settings):
    """Test storing encrypted token with plain string."""
    token = "my-oauth-token"

    store_encrypted_token(mock_request, token, mock_settings)

    assert "access_token" in mock_request.session
    assert mock_request.session["authenticated"] is True


def test_get_decrypted_token_success(mock_request, mock_settings):
    """Test retrieving and decrypting token from session."""
    original_token = SecretStr("my-oauth-token")

    # Store encrypted token
    store_encrypted_token(mock_request, original_token, mock_settings)

    # Retrieve and decrypt
    decrypted = get_decrypted_token(mock_request, mock_settings)

    assert decrypted is not None
    assert decrypted.get_secret_value() == original_token.get_secret_value()


def test_get_decrypted_token_not_found(mock_request, mock_settings):
    """Test retrieving token when none exists."""
    result = get_decrypted_token(mock_request, mock_settings)

    assert result is None


def test_get_decrypted_token_invalid_data(mock_request, mock_settings):
    """Test retrieving token with invalid encrypted data."""
    mock_request.session = {"access_token": "invalid-encrypted-data"}

    result = get_decrypted_token(mock_request, mock_settings)

    assert result is None


def test_is_authenticated_true(mock_request):
    """Test is_authenticated returns True when authenticated."""
    mock_request.session = {"authenticated": True}

    result = is_authenticated(mock_request)

    assert result is True


def test_is_authenticated_false(mock_request):
    """Test is_authenticated returns False when not authenticated."""
    mock_request.session = {"authenticated": False}

    result = is_authenticated(mock_request)

    assert result is False


def test_is_authenticated_missing(mock_request):
    """Test is_authenticated returns False when key missing."""
    result = is_authenticated(mock_request)

    assert result is False


def test_is_authenticated_without_session():
    """Test is_authenticated when session doesn't exist."""
    request = MagicMock(spec=[])

    result = is_authenticated(request)

    assert result is False
