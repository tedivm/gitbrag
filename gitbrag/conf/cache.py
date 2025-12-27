from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Cache control
    cache_enabled: bool = False

    # Redis configuration
    cache_redis_host: str | None = None
    cache_redis_port: int = 6379

    # Default TTLs (in seconds)
    cache_default_ttl: int = 300  # 5 minutes for memory cache
    cache_persistent_ttl: int = 3600  # 1 hour for persistent cache
    cache_star_increase_ttl: int = 86400  # 24 hours for star increase data (historical data doesn't change)
