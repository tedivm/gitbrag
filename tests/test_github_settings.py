import pytest
from pydantic import SecretStr, ValidationError

from gitbrag.conf.github import GitHubAuthType, GitHubSettings


def test_pat_configuration_valid() -> None:
    """Test valid PAT authentication configuration."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.PAT,
        github_token=SecretStr("test_token_123"),
    )
    assert settings.github_auth_type == GitHubAuthType.PAT
    assert settings.github_token is not None
    assert settings.github_token.get_secret_value() == "test_token_123"


def test_pat_configuration_missing_token() -> None:
    """Test PAT configuration fails without token."""
    with pytest.raises(ValidationError, match="github_token is required"):
        GitHubSettings(
            github_auth_type=GitHubAuthType.PAT,
            github_token=None,
            github_validate_on_init=True,
        )


def test_github_app_configuration_valid() -> None:
    """Test valid GitHub App OAuth configuration."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.GITHUB_APP,
        github_app_client_id="test_client_id",
        github_app_client_secret=SecretStr("test_client_secret"),
    )
    assert settings.github_auth_type == GitHubAuthType.GITHUB_APP
    assert settings.github_app_client_id == "test_client_id"
    assert settings.github_app_client_secret is not None
    assert settings.github_app_client_secret.get_secret_value() == "test_client_secret"


def test_github_app_configuration_missing_client_id() -> None:
    """Test GitHub App configuration fails without client ID."""
    with pytest.raises(ValidationError, match="github_app_client_id is required"):
        GitHubSettings(
            github_auth_type=GitHubAuthType.GITHUB_APP,
            github_app_client_id=None,
            github_app_client_secret=SecretStr("test_secret"),
            github_validate_on_init=True,
        )


def test_github_app_configuration_missing_client_secret() -> None:
    """Test GitHub App configuration fails without client secret."""
    with pytest.raises(ValidationError, match="github_app_client_secret is required"):
        GitHubSettings(
            github_auth_type=GitHubAuthType.GITHUB_APP,
            github_app_client_id="test_id",
            github_app_client_secret=None,
            github_validate_on_init=True,
        )


def test_oauth_callback_port_default() -> None:
    """Test default OAuth callback port."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.PAT,
        github_token=SecretStr("test_token"),
    )
    assert settings.github_oauth_callback_port == 8080


def test_oauth_callback_port_custom() -> None:
    """Test custom OAuth callback port."""
    settings = GitHubSettings(
        github_auth_type=GitHubAuthType.PAT,
        github_token=SecretStr("test_token"),
        github_oauth_callback_port=9000,
    )
    assert settings.github_oauth_callback_port == 9000


def test_oauth_callback_port_invalid_low() -> None:
    """Test OAuth callback port validation rejects ports below 1024."""
    with pytest.raises(ValidationError, match="OAuth callback port must be between 1024 and 65535"):
        GitHubSettings(
            github_auth_type=GitHubAuthType.PAT,
            github_token=SecretStr("test_token"),
            github_oauth_callback_port=80,
        )


def test_oauth_callback_port_invalid_high() -> None:
    """Test OAuth callback port validation rejects ports above 65535."""
    with pytest.raises(ValidationError, match="OAuth callback port must be between 1024 and 65535"):
        GitHubSettings(
            github_auth_type=GitHubAuthType.PAT,
            github_token=SecretStr("test_token"),
            github_oauth_callback_port=70000,
        )


def test_auth_type_enum() -> None:
    """Test GitHubAuthType enum values."""
    assert GitHubAuthType.PAT == "pat"
    assert GitHubAuthType.GITHUB_APP == "github_app"


def test_environment_variable_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings from environment variables."""
    monkeypatch.setenv("GITHUB_AUTH_TYPE", "pat")
    monkeypatch.setenv("GITHUB_TOKEN", "env_token_123")

    settings = GitHubSettings()
    assert settings.github_auth_type == GitHubAuthType.PAT
    assert settings.github_token is not None
    assert settings.github_token.get_secret_value() == "env_token_123"
