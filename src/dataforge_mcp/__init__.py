"""DataForge Semantic MCP Server — library-first package.

Usage as library (no MCP needed):

    from dataforge_mcp import create_semantic_service

    service = create_semantic_service()
    projects = await service.list_projects()
    rmd = await service.get_rmd(project_id=392, version_id=948)

Usage as MCP server:

    python -m dataforge_mcp
"""

from __future__ import annotations

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.cache.file_store import FileCacheStore
from dataforge_mcp.config import Settings, get_settings
from dataforge_mcp.dataforge.client import DataForgeClient


def create_semantic_service(
    settings: Settings | None = None,
) -> SemanticService:
    """Create a SemanticService instance ready for use as a Python library.

    Args:
        settings: Optional Settings override. If None, loads from env / .env.

    Returns:
        SemanticService with client and cache configured.
    """
    if settings is None:
        settings = get_settings()

    client = DataForgeClient(
        base_url=settings.dataforge_base_url,
        api_key=settings.dataforge_api_key,
    )
    cache = FileCacheStore(cache_dir=settings.cache_dir)
    return SemanticService(client=client, cache=cache, settings=settings)


__all__ = ["create_semantic_service", "SemanticService"]
