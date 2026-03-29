# 10. Build Prompts

Ниже — готовые промпты, которыми можно поэтапно собирать новый продукт в Claude Code, Cursor, Copilot Chat или другой coding assistant.

---

## Промпт 1. Bootstrap репозитория

Создай новый Python-проект `dataforge-semantic-mcp`.

Это отдельный MCP-сервер, который подключается только к DataForge Product API и отдает семантический слой в AI-агенты.

Важно:
- НЕ подключай никакие базы данных
- НЕ реализуй SQL execution
- НЕ добавляй text-to-sql
- только read-only semantic access

Нужна структура:

- `src/dataforge_mcp/main.py`
- `src/dataforge_mcp/config.py`
- `src/dataforge_mcp/logging.py`
- `src/dataforge_mcp/errors.py`
- `src/dataforge_mcp/dataforge/client.py`
- `src/dataforge_mcp/dataforge/schemas.py`
- `src/dataforge_mcp/semantic/models.py`
- `src/dataforge_mcp/semantic/normalizer.py`
- `src/dataforge_mcp/cache/store.py`
- `src/dataforge_mcp/cache/file_store.py`
- `src/dataforge_mcp/application/use_cases.py`
- `src/dataforge_mcp/mcp/server.py`
- `src/dataforge_mcp/mcp/tools.py`
- `tests/`

Стек:
- Python 3.11+
- httpx
- pydantic
- pydantic-settings
- structlog
- mcp

Собери также:
- `pyproject.toml`
- `.env.example`
- `README.md`

---

## Промпт 2. DataForge client

Реализуй `DataForgeClient` для работы с DataForge Product API.

Нужно поддержать endpoints:

- `GET /rmd-api/v1/projects`
- `GET /rmd-api/v1/projects/{projectId}/versions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/measures`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd`

Требования:
- использовать `httpx.AsyncClient`
- передавать `X-Api-Key`
- base URL брать из config
- поддерживать timeout
- сделать нормальную обработку 401 и 404
- вернуть typed Pydantic models
- не логировать секреты

---

## Промпт 3. Semantic normalization

Реализуй слой нормализации DataForge RMD.

Нужно:

1. Сделать канонические модели:
- `CanonicalProject`
- `CanonicalVersion`
- `CanonicalMeasure`
- `CanonicalDimension`
- `CanonicalSemanticContext`

2. Реализовать функции:
- `normalize_project`
- `normalize_version`
- `normalize_measure`
- `normalize_dimension`
- `build_semantic_context`
- `build_semantic_summary`

Требования:
- для measures переименовать `measure_name` в `name`, `measure_description` в `description`
- для dimensions переименовать `dimension_name` в `name`, `dimension_description` в `description`
- сохранять исходный объект в `raw`
- добавлять stats: `measure_count`, `dimension_count`

---

## Промпт 4. Cache layer

Реализуй файловый кэш для semantic responses.

Нужно:
- `CacheStore` interface
- `FileCacheStore`
- TTL
- cache keys по `(project_id, version_id, language, entity_type)`
- force refresh
- last-known-good fallback

Папка кэша должна задаваться через config.

Каждая запись кэша должна хранить:
- `fetched_at`
- `ttl_seconds`
- `payload`

---

## Промпт 5. MCP tools

Реализуй MCP server и tools для DataForge semantic access.

Обязательные tools:
- `df_health`
- `df_list_projects`
- `df_list_versions`
- `df_get_measures`
- `df_get_dimensions`
- `df_get_rmd`
- `df_refresh_cache`

Требования:
- tools должны вызывать use cases, а не client напрямую
- все ответы JSON-совместимы
- ошибки должны возвращаться в нормализованном формате
- не добавляй SQL tools

---

## Промпт 6. Tests

Добавь тесты для:
- `DataForgeClient`
- `normalize_measure`
- `normalize_dimension`
- `build_semantic_context`
- `FileCacheStore`
- MCP tools

Используй:
- `pytest`
- `pytest-asyncio`
- `respx`

Покрой happy path и error path.

---

## Промпт 7. Packaging

Сделай проект готовым к запуску как отдельный продукт.

Нужно:
- `python -m dataforge_mcp`
- Dockerfile
- example run command
- README с инструкцией запуска
- `.env.example`

Добавь отдельный раздел в README:
- scope
- supported DataForge endpoints
- MCP tools
- out-of-scope
