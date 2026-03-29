"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dataforge_base_url: str = "https://api.prod-df.businessqlik.com"
    dataforge_api_key: SecretStr = SecretStr("replace_me")
    default_language: str = "ru"
    cache_backend: str = "file"
    cache_dir: str = "./cache"
    cache_ttl_seconds: int = 3600
    mcp_server_name: str = "dataforge-semantic"
    mcp_transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
