from enum import Enum

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings


class GitHubAuthType(str, Enum):
    """Supported GitHub authentication types."""

    PAT = "pat"
    GITHUB_APP = "github_app"


class GitHubSettings(BaseSettings):
    """GitHub API configuration and authentication settings."""

    # Authentication type
    github_auth_type: GitHubAuthType = Field(
        default=GitHubAuthType.PAT,
        description="Authentication type for GitHub API (pat or github_app)",
    )

    # Personal Access Token authentication
    github_token: SecretStr | None = Field(
        default=None,
        description="GitHub Personal Access Token for API authentication",
    )

    # GitHub App OAuth authentication
    github_app_client_id: str | None = Field(
        default=None,
        description="GitHub App client ID for OAuth authentication",
    )
    github_app_client_secret: SecretStr | None = Field(
        default=None,
        description="GitHub App client secret for OAuth authentication",
    )

    # OAuth callback configuration
    github_oauth_callback_port: int = Field(
        default=8080,
        description="Port for local OAuth callback server",
    )

    @field_validator("github_oauth_callback_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate OAuth callback port is in valid range."""
        if not 1024 <= v <= 65535:
            raise ValueError("OAuth callback port must be between 1024 and 65535")
        return v

    # Disable validation by default - only validate when actually using GitHub features
    github_validate_on_init: bool = Field(
        default=False,
        description="Whether to validate GitHub auth config on initialization",
    )

    @model_validator(mode="after")
    def validate_auth_config(self) -> "GitHubSettings":
        """Validate that required authentication fields are set for the selected auth type."""
        # Skip validation unless explicitly enabled
        if not self.github_validate_on_init:
            return self

        if self.github_auth_type == GitHubAuthType.PAT:
            if self.github_token is None:
                raise ValueError("github_token is required when using PAT authentication")
        elif self.github_auth_type == GitHubAuthType.GITHUB_APP:
            if self.github_app_client_id is None:
                raise ValueError("github_app_client_id is required when using GitHub App authentication")
            if self.github_app_client_secret is None:
                raise ValueError("github_app_client_secret is required when using GitHub App authentication")
        return self
