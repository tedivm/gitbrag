from .cache import CacheSettings


class Settings(CacheSettings):
    project_name: str = "gitbrag"
    debug: bool = False
