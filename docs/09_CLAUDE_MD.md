# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

This repository contains a standalone MCP server for the DataForge semantic layer.

The server connects only to DataForge Product API and exposes the semantic layer to AI agents through MCP.

Current scope is strictly limited to read-only semantic access:

- list projects
- list project versions
- fetch measures
- fetch dimensions
- fetch full RMD
- normalize semantic metadata
- cache responses

Out of scope for now:

- SQL execution
- text-to-SQL
- database connections
- schema introspection from DWH
- BI rendering

## Architecture Principles

Keep the code separated into the following concerns:

- `dataforge/` for Product API access
- `semantic/` for normalization and summaries
- `cache/` for cache storage
- `application/` for use cases
- `mcp/` for MCP tool registration and transport

Do not mix MCP transport details with DataForge client logic.

## Technical Rules

- Python 3.11+
- Type hints everywhere
- Pydantic models for external responses and canonical models
- `httpx` for HTTP requests
- `structlog` for structured logging
- `pydantic-settings` for config
- no hardcoded secrets
- comments and code in English

## Product API Rules

Always send `X-Api-Key` header to DataForge Product API.

Base URL must come from config.

Support these endpoints:

- `/rmd-api/v1/projects`
- `/rmd-api/v1/projects/{projectId}/versions`
- `/rmd-api/v1/projects/{projectId}/versions/{versionId}/measures`
- `/rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions`
- `/rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd`

## MCP Tools

Main tools to support in MVP:

- `df_health`
- `df_list_projects`
- `df_list_versions`
- `df_get_measures`
- `df_get_dimensions`
- `df_get_rmd`
- `df_refresh_cache`

Optional later:

- `df_get_semantic_summary`
- `df_search_semantic_entities`

## Cache

Use a transparent cache layer.

The cache must support:
- TTL
- force refresh
- last-known-good fallback

## Errors

Map DataForge API errors to internal normalized error codes.

Never leak secrets into logs or tool responses.

## Testing

Tests should cover:
- DataForge client
- normalizer
- cache
- MCP tools

At least one integration path should cover:
projects -> versions -> rmd.
