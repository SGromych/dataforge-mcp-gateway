# 07. Repository Bootstrap

## Имя репозитория

Рекомендуемое имя:

`dataforge-semantic-mcp`

Альтернативы:

- `dataforge-mcp-semantic-server`
- `dataforge-rmd-mcp`
- `dataforge-semantic-gateway`

## Структура репозитория

```text
dataforge-semantic-mcp/
├── src/
│   └── dataforge_mcp/
│       ├── __init__.py
│       ├── main.py
│       ├── cli.py
│       ├── config.py
│       ├── logging.py
│       ├── errors.py
│       ├── transport/
│       │   ├── __init__.py
│       │   ├── stdio.py
│       │   └── sse.py
│       ├── application/
│       │   ├── __init__.py
│       │   ├── services.py
│       │   └── use_cases.py
│       ├── dataforge/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── endpoints.py
│       │   ├── schemas.py
│       │   └── mapper.py
│       ├── semantic/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── normalizer.py
│       │   └── summary.py
│       ├── cache/
│       │   ├── __init__.py
│       │   ├── store.py
│       │   └── file_store.py
│       └── mcp/
│           ├── __init__.py
│           ├── server.py
│           └── tools.py
├── tests/
│   ├── test_client.py
│   ├── test_normalizer.py
│   ├── test_cache.py
│   └── test_tools.py
├── docs/
├── .env.example
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Минимальный `pyproject.toml`

```toml
[project]
name = "dataforge-semantic-mcp"
version = "0.1.0"
description = "MCP server for DataForge semantic layer"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "structlog>=24.1",
    "mcp>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.3",
]
```

## Почему здесь не нужен FastAPI в ядре

Так как сейчас задача — только MCP и Product API, FastAPI не обязателен для первого запуска.

Можно пойти двумя путями.

### Вариант А. MCP-first

Делать только:
- stdio transport
- optional SSE transport позже

Плюсы:
- проще
- меньше кода
- чище фокус

### Вариант Б. Hybrid

Сразу добавить маленький HTTP слой ради `/health` и SSE.

Плюсы:
- удобнее эксплуатация
- проще health checks
- проще интеграция с docker/k8s probes

Для MVP я рекомендую:

- stdio как обязательный режим
- health endpoint и SSE как второй шаг

## Основные пакеты

### `dataforge/client.py`

Только работа с Product API.

### `semantic/normalizer.py`

Только преобразование raw -> canonical.

### `application/use_cases.py`

Сценарии, которые вызывают и client, и cache, и normalizer.

### `mcp/tools.py`

Регистрация MCP tools. Здесь не должно быть сложной бизнес-логики.

## Что можно взять из текущих наработок

Из старого прототипа полезно взять не код целиком, а только идеи:

- из `rmd_downloader.py` — подход с загрузкой full RMD и кэшированием
- из `rmd_loader.py` — идею выбора источника RMD
- из `mcp_server.py` — понимание минимального MCP фасада
- из старых markdown — структуру rollout и naming

Но новый репозиторий нужно писать заново, без прямого импорта donor-файлов.
