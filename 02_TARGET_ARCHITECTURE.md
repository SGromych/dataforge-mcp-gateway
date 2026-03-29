# 02. Target Architecture

## Общая схема

Архитектура сервера должна быть простой и предсказуемой.

```text
AI Agent / MCP Client
        │
        │  MCP (stdio or SSE)
        ▼
DataForge Semantic MCP Server
        │
        │  HTTPS + X-Api-Key
        ▼
DataForge Product API
        │
        ├── /rmd-api/v1/projects
        ├── /rmd-api/v1/projects/{projectId}/versions
        ├── /rmd-api/v1/projects/{projectId}/versions/{versionId}/measures
        ├── /rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions
        └── /rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd
```

## Логические слои

### 1. Transport Layer

Этот слой отвечает за MCP-протокол.

Он должен поддерживать:

- `stdio` для desktop MCP-клиентов
- `SSE` для серверных и web-based интеграций

Его задача — принять MCP-запрос, вызвать доменный сервис и вернуть результат в формате MCP tool response.

### 2. Application Layer

Этот слой реализует сценарии использования:

- list projects
- list versions
- get measures
- get dimensions
- get full rmd
- refresh cache
- get normalized semantic context

Это основной orchestration layer.

### 3. DataForge Client Layer

Этот слой инкапсулирует работу с Product API.

Он должен:
- формировать URL
- подставлять `X-Api-Key`
- отправлять запросы
- обрабатывать pagination
- различать ошибки аутентификации, доступа и not found
- возвращать строго typed response objects

### 4. Normalization Layer

Сырой ответ Product API полезен, но не идеален для AI-агентов.

Нужен отдельный слой нормализации, который:
- приводит поля к единой схеме
- делает предсказуемые названия сущностей
- строит компактные summaries
- умеет собирать "semantic context" из measures и dimensions

### 5. Cache Layer

Этот слой нужен, чтобы:
- не дергать Product API при каждом запросе
- уменьшить задержки
- защищаться от limit spikes
- сохранять last-known-good copy

На старте достаточно файлового кэша.
Дальше можно добавить Redis или internal SQLite/PostgreSQL.

### 6. Observability Layer

Сервер должен писать:
- структурированные логи
- ошибки Product API
- статистику по tool calls
- cache hit / miss
- время ответа

## Рекомендуемая структура модулей

```text
dataforge-semantic-mcp/
├── src/dataforge_mcp/
│   ├── __init__.py
│   ├── main.py
│   ├── cli.py
│   ├── config.py
│   ├── logging.py
│   ├── transport/
│   │   ├── __init__.py
│   │   ├── mcp_stdio.py
│   │   └── mcp_sse.py
│   ├── application/
│   │   ├── __init__.py
│   │   ├── services.py
│   │   └── use_cases.py
│   ├── dataforge/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── endpoints.py
│   │   ├── auth.py
│   │   └── schemas.py
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── summarizer.py
│   │   └── models.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── keys.py
│   └── api/
│       ├── __init__.py
│       └── health.py
├── tests/
├── docs/
├── pyproject.toml
├── .env.example
└── README.md
```

## Почему такая архитектура лучше прототипа

В текущем прототипе у вас один файл читает локальный JSON и отдает его наружу. В новой схеме семантика не захардкожена в файл и не зависит от заранее скачанного артефакта.

Вместо этого:

- источник семантики — Product API DataForge
- кэш — управляемый
- MCP tools — стабильные
- транспорт отделен от бизнес-логики
- ответы нормализованы
- код пригоден для сопровождения и расширения

## Каноническая внутренняя модель

Нужно ввести внутреннюю каноническую модель семантического слоя.

### CanonicalProject

- `id`
- `name`
- `description`

### CanonicalVersion

- `id`
- `name`
- `is_global`

### CanonicalMeasure

- `row_number`
- `group`
- `block`
- `name`
- `description`
- `data_type`
- `measure_type`
- `formula`
- `restrictions`
- `connected_source`
- `status`
- `relevance`
- `required`
- `visibility`
- `responsible_for_data`
- `variation`
- `raw`

### CanonicalDimension

- `row_number`
- `group`
- `block`
- `name`
- `description`
- `dimension_group`
- `data_type`
- `connected_source`
- `value_options`
- `status`
- `relevance`
- `required`
- `visibility`
- `responsible_for_data`
- `raw`

### CanonicalSemanticContext

- `project`
- `version`
- `measures`
- `dimensions`
- `summary`
- `stats`

Именно эта модель должна быть внутренним контрактом между слоями.
