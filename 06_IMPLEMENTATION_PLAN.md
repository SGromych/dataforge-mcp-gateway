# 06. Implementation Plan

## Общий подход

Реализовывать надо не все сразу, а по слоям. Каждая стадия должна завершаться рабочим, тестируемым состоянием.

## Этап 1. Bootstrap проекта

Цель — создать пустой, но корректный каркас.

Что сделать:

- создать новый репозиторий
- собрать `pyproject.toml`
- добавить базовую структуру пакета
- завести `.env.example`
- подключить линтер и pytest
- сделать `main.py`
- сделать простой `df_health`

Результат этапа:
- сервер запускается
- MCP transport инициализируется
- есть health endpoint

## Этап 2. DataForge API client

Цель — получить чистый клиент Product API.

Что сделать:

- класс `DataForgeClient`
- методы:
  - `get_projects`
  - `get_versions`
  - `get_measures`
  - `get_dimensions`
  - `get_rmd`
- общий HTTP client
- обработка заголовка `X-Api-Key`
- timeout и retry
- error mapping

Результат этапа:
- локальный unit test на client проходит
- можно получить данные из реального Product API

## Этап 3. Typed schemas

Цель — убрать хаос словарей.

Что сделать:

- Pydantic models для:
  - `ProjectListResponse`
  - `VersionListResponse`
  - `MeasureRaw`
  - `DimensionRaw`
  - `RmdRaw`
- канонические модели:
  - `CanonicalMeasure`
  - `CanonicalDimension`
  - `CanonicalSemanticContext`

Результат этапа:
- все входы и выходы типизированы
- нормализация работает предсказуемо

## Этап 4. Normalization layer

Цель — перевести Product API ответы в AI-friendly модели.

Что сделать:

- `normalize_measure`
- `normalize_dimension`
- `build_semantic_context`
- `build_summary`
- `compute_stats`

Результат этапа:
- сервер может вернуть полный и сокращенный semantic context

## Этап 5. Cache layer

Цель — убрать излишние вызовы Product API.

Что сделать:

- `CacheStore` interface
- `FileCacheStore`
- TTL check
- force refresh
- last-known-good fallback

Результат этапа:
- повторные вызовы не ходят в Product API без необходимости

## Этап 6. MCP tools

Цель — открыть функциональность через MCP.

Что сделать:

- зарегистрировать tools
- описать input/output schemas
- связать tools с use cases
- добавить error objects

Результат этапа:
- MCP клиент получает семантику DataForge через tools

## Этап 7. SSE transport

Цель — поддержать серверные агенты и web-интеграции.

Что сделать:

- поднять SSE transport
- продумать auth на уровне reverse proxy или internal key
- добавить health route

Результат этапа:
- сервер может использоваться не только через stdio

## Этап 8. Observability

Цель — сделать сервис сопровождемым.

Что сделать:

- structlog
- request_id
- tool metrics
- cache metrics
- error metrics

Результат этапа:
- можно диагностировать проблемы и смотреть usage

## Этап 9. Packaging

Цель — сделать продукт переносимым.

Что сделать:

- Dockerfile
- docker-compose example
- запуск через `python -m`
- release notes

Результат этапа:
- сервер можно развернуть как отдельный продукт

## Предлагаемый порядок по дням

### День 1
- repo bootstrap
- config
- logging
- health

### День 2
- DataForge client
- get_projects
- get_versions

### День 3
- get_measures
- get_dimensions
- get_rmd

### День 4
- typed schemas
- normalizer

### День 5
- cache layer

### День 6
- MCP stdio tools

### День 7
- SSE transport

### День 8
- tests
- docker
- docs cleanup

## Definition of Done для MVP

MVP можно считать готовым, когда выполняются все условия:

- сервер поднимается как отдельный процесс
- работает stdio MCP transport
- работает минимум 6 tools
- идет реальное чтение из DataForge Product API
- поддерживаются projects, versions, measures, dimensions, full rmd
- кэш работает
- ошибки DataForge маппятся в понятные серверные ошибки
- есть README и `.env.example`
- есть тесты на client и normalizer
