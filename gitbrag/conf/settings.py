from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .cache import CacheSettings
from .github import GitHubSettings


class WebSettings(BaseSettings):
    """Web interface configuration settings."""

    # Session management
    session_secret_key: SecretStr | None = Field(
        default=None,
        description="Secret key for session signing and token encryption (required for web interface)",
    )
    session_max_age: int = Field(
        default=86400,  # 24 hours
        description="Session expiration time in seconds",
    )

    # OAuth configuration
    oauth_callback_url: str = Field(
        default="http://localhost/auth/callback",
        description="Full URL for OAuth callback (e.g., https://yourdomain.com/auth/callback)",
    )

    # Security settings
    require_https: bool = Field(
        default=False,
        description="Require HTTPS for secure cookies (set True in production)",
    )

    # OAuth scopes
    oauth_scopes: str = Field(
        default="read:user",
        description="OAuth scopes to request (minimal: read:user for public data)",
    )

    # Cache staleness threshold
    report_cache_stale_age: int = Field(
        default=86400,  # 24 hours
        description="Age in seconds when cached reports are considered stale and should be refreshed",
    )

    # Example user for home page
    example_username: str = Field(
        default="tedivm",
        description="GitHub username to use as an example on the home page",
    )

    # Task tracking settings
    task_timeout_seconds: int = Field(
        default=300,
        description="Timeout in seconds for background tasks (auto-cleanup if task hangs)",
    )
    max_reported_user_concurrent_tasks: int = Field(
        default=1,
        description="Maximum concurrent report generation tasks per reported GitHub username",
    )

    # Analytics settings
    enable_plausible: bool = Field(
        default=False,
        description="Enable Plausible Analytics privacy-friendly tracking. Requires PLAUSIBLE_SCRIPT_HASH to be set.",
    )
    plausible_script_hash: str | None = Field(
        default=None,
        description="Site-specific Plausible script hash (e.g., 'pa-HQtsjLCgyK7ys8q_iRTLl'). Find this in your Plausible site settings under 'Site Installation'.",
    )


class Settings(CacheSettings, GitHubSettings, WebSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "gitbrag"
    debug: bool = False
