"""MCP tool registration — thin wrappers delegating to SemanticService.

Tool definitions live in :mod:`.tools_read` and :mod:`.tools_write`; dispatch is a flat
registry rather than a match statement so that "every tool has a handler and every
handler has a tool" is a one-line test.

The two protocol handlers are built here and handed to :class:`mcp.server.Server` as
``on_list_tools`` / ``on_call_tool``. That is the registration API of the MCP SDK 2.x,
which replaced the ``@server.list_tools()`` decorators of 1.x. The SDK no longer
validates tool arguments either, so :mod:`.arguments` does it — and does it in the
error envelope this server documents.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)
from pydantic import ValidationError

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.dataforge.write_schemas import validation_error_fields
from dataforge_mcp.errors import DataForgeError, ErrorCode
from dataforge_mcp.logging import get_logger

from .arguments import prepare_arguments
from .tools_read import READ_HANDLERS, Handler, build_read_tools
from .tools_write import WRITE_HANDLERS, build_write_tools

logger = get_logger(__name__)

HANDLERS: dict[str, Handler] = {**READ_HANDLERS, **WRITE_HANDLERS}

ListToolsHandler = Callable[
    [ServerRequestContext[Any], PaginatedRequestParams | None], Awaitable[ListToolsResult]
]
CallToolHandler = Callable[
    [ServerRequestContext[Any], CallToolRequestParams], Awaitable[CallToolResult]
]


def _build_tools(default_language: str) -> list[Tool]:
    return [*build_read_tools(default_language), *build_write_tools(default_language)]


def build_tool_handlers(service: SemanticService) -> tuple[ListToolsHandler, CallToolHandler]:
    """Build the ``(on_list_tools, on_call_tool)`` pair for the low-level server."""
    tools = _build_tools(service.settings.default_language)
    tools_by_name = {tool.name: tool for tool in tools}

    async def on_list_tools(
        ctx: ServerRequestContext[Any],
        params: PaginatedRequestParams | None = None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    async def on_call_tool(
        ctx: ServerRequestContext[Any],
        params: CallToolRequestParams,
    ) -> CallToolResult:
        name = params.name
        arguments = dict(params.arguments or {})
        failed = True

        try:
            tool = tools_by_name.get(name)
            if tool is not None:
                arguments = prepare_arguments(tool.input_schema, arguments)
            result = await _dispatch(name, arguments, service)
            failed = "error" in result
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

        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            isError=failed,
        )

    return on_list_tools, on_call_tool


async def _dispatch(name: str, args: dict[str, Any], service: SemanticService) -> dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {name}"}}
    return await handler(args, service)
