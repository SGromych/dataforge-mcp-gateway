"""Transport layer: stdio, Streamable HTTP, and the deprecated HTTP+SSE.

`run_transport` is the single dispatch point. Both entry points - `main.py` for
`python -m dataforge_mcp` and `cli.py` for the `dataforge-mcp` script - go
through it, so adding a transport touches one place instead of three.
"""

from __future__ import annotations

from mcp.server import Server

from dataforge_mcp.config import TRANSPORTS, Settings
from dataforge_mcp.logging import get_logger

logger = get_logger(__name__)

__all__ = ["TRANSPORTS", "run_transport"]


async def run_transport(server: Server, settings: Settings) -> None:
    """Serve `server` over the transport named by `settings.mcp_transport`.

    The value is already validated by `Settings`, so there is no silent
    fallback here: an unknown transport cannot reach this function.
    """
    if settings.mcp_transport == "streamable-http":
        from .streamable_http import run_streamable_http

        await run_streamable_http(server, settings)
        return

    if settings.mcp_transport == "sse":
        logger.warning(
            "transport_deprecated",
            transport="sse",
            message=(
                "The HTTP+SSE transport was deprecated in MCP revision 2025-03-26 and "
                "will be removed. Use MCP_TRANSPORT=streamable-http instead."
            ),
        )
        from .sse import run_sse

        await run_sse(server, settings)
        return

    from .stdio import run_stdio

    await run_stdio(server)
