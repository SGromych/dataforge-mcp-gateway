"""MCP tool registration — thin wrappers delegating to SemanticService.

Tool definitions live in :mod:`.tools_read` and :mod:`.tools_write`; dispatch is a flat
registry rather than a match statement so that "every tool has a handler and every
handler has a tool" is a one-line test.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import ValidationError

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.dataforge.write_schemas import validation_error_fields
from dataforge_mcp.errors import DataForgeError, ErrorCode
from dataforge_mcp.logging import get_logger

from .tools_read import READ_HANDLERS, Handler, build_read_tools
from .tools_write import WRITE_HANDLERS, build_write_tools

logger = get_logger(__name__)

HANDLERS: dict[str, Handler] = {**READ_HANDLERS, **WRITE_HANDLERS}


def _build_tools(default_language: str) -> list[Tool]:
    return [*build_read_tools(default_language), *build_write_tools(default_language)]


def register_tools(server: Server, service: SemanticService) -> None:
    tools = _build_tools(service.settings.default_language)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            result = await _dispatch(name, arguments, service)
        except DataForgeError as exc:
            result = exc.to_dict()
        except ValidationError as exc:
            # Local body validation must look exactly like the server's own 400.
            result = DataForgeError(
                code=ErrorCode.DATAFORGE_VALIDATION_FAILED,
                message="Invalid tool arguments",
                field_errors=validation_error_fields(exc),
            ).to_dict()
        except KeyError as exc:
            result = DataForgeError(
                code=ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD,
                message=f"Missing required argument: {exc.args[0]}",
                field_errors=[{"field": str(exc.args[0]), "code": "missing_field"}],
            ).to_dict()
        except Exception as exc:  # noqa: BLE001 - never break the protocol
            logger.error("tool_failed", tool_name=name, error=type(exc).__name__)
            result = DataForgeError(
                code=ErrorCode.DATAFORGE_INTERNAL_ERROR,
                message=f"{type(exc).__name__}: {exc}",
            ).to_dict()

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def _dispatch(name: str, args: dict[str, Any], service: SemanticService) -> dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {name}"}}
    return await handler(args, service)
