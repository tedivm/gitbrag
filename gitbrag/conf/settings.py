from pydantic_settings import SettingsConfigDict

from .cache import CacheSettings
from .github import GitHubSettings


class Settings(CacheSettings, GitHubSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "gitbrag"
    debug: bool = False
