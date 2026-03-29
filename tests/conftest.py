"""Shared test fixtures."""

import pytest

from dataforge_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        dataforge_base_url="https://api.test.example.com",
        dataforge_api_key="test-api-key-12345",
        cache_dir="./test_cache",
        cache_ttl_seconds=60,
        log_level="DEBUG",
    )
