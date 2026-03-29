# 03. MCP Tools Specification

## Общий принцип

MCP-сервер должен предоставлять не один универсальный tool, а несколько узкоспециализированных tools, каждый из которых решает понятную задачу.

Это делает поведение сервера более предсказуемым для AI-агентов и уменьшает размер ответов.

## Tool 1. `df_health`

### Назначение

Проверяет, что сервер жив, конфигурация загружена и Product API доступен.

### Вход

```json
{}
```

### Выход

```json
{
  "server_status": "ok",
  "product_api_status": "ok",
  "base_url": "https://api.prod-df.businessqlik.com",
  "cache_status": "ok"
}
```

## Tool 2. `df_list_projects`

### Назначение

Возвращает список проектов, доступных через указанный DataForge API key.

### Вход

```json
{
  "page": 1,
  "page_size": 100,
  "use_cache": true
}
```

### Выход

```json
{
  "projects": [
    {
      "id": 1,
      "name": "Project Name",
      "description": "Project Description"
    }
  ],
  "pagination": {
    "total": 10,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

## Tool 3. `df_list_versions`

### Назначение

Возвращает версии конкретного проекта.

### Вход

```json
{
  "project_id": 392,
  "page": 1,
  "page_size": 100,
  "use_cache": true
}
```

### Выход

```json
{
  "project_id": 392,
  "versions": [
    {
      "id": 948,
      "name": "Version Name",
      "is_global": true
    }
  ]
}
```

## Tool 4. `df_get_measures`

### Назначение

Возвращает все measures выбранной версии проекта.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "language": "ru",
  "use_cache": true
}
```

### Выход

```json
{
  "project_id": 392,
  "version_id": 948,
  "measures": [
    {
      "name": "Общий доход",
      "group": "Продажи",
      "block": "Доход",
      "description": "Общий доход от всех продаж",
      "data_type": "Числовой",
      "measure_type": "Сумма",
      "formula": "[Revenue]",
      "connected_source": {
        "db": "Sales DB",
        "schema": null,
        "table": "sales_table",
        "column": null
      },
      "status": "Активный",
      "required": true,
      "raw": {}
    }
  ]
}
```

## Tool 5. `df_get_dimensions`

### Назначение

Возвращает все dimensions выбранной версии проекта.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "language": "ru",
  "use_cache": true
}
```

### Выход

```json
{
  "project_id": 392,
  "version_id": 948,
  "dimensions": [
    {
      "name": "ID клиента",
      "group": "Продажи",
      "block": "Клиент",
      "description": "Уникальный идентификатор клиента",
      "dimension_group": "Атрибуты клиента",
      "data_type": "Строка",
      "connected_source": {
        "db": 161,
        "schema": null,
        "table": "customers",
        "column": "CompanyName"
      },
      "status": "Активный",
      "required": true,
      "raw": {}
    }
  ]
}
```

## Tool 6. `df_get_rmd`

### Назначение

Возвращает полный RMD в нормализованном виде.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "language": "ru",
  "use_cache": true,
  "include_raw": false
}
```

### Выход

```json
{
  "project": {
    "id": 392,
    "name": "Fashion Retail"
  },
  "version": {
    "id": 948,
    "name": "Global Version",
    "is_global": true
  },
  "measures": [],
  "dimensions": [],
  "stats": {
    "measure_count": 120,
    "dimension_count": 75
  }
}
```

## Tool 7. `df_get_semantic_summary`

### Назначение

Возвращает сокращенную AI-friendly сводку по семантическому слою.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "language": "ru",
  "max_items_per_group": 20
}
```

### Выход

```json
{
  "project_name": "Fashion Retail",
  "version_name": "Global Version",
  "summary": {
    "measure_groups": [
      {
        "group": "Продажи",
        "blocks": [
          {
            "block": "Доход",
            "measure_names": ["Общий доход", "Чистая выручка"]
          }
        ]
      }
    ],
    "dimension_groups": [
      {
        "group": "Продажи",
        "blocks": [
          {
            "block": "Клиент",
            "dimension_names": ["ID клиента", "Сегмент клиента"]
          }
        ]
      }
    ]
  }
}
```

## Tool 8. `df_refresh_cache`

### Назначение

Принудительно обновляет кэш по конкретному проекту и версии.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "language": "ru"
}
```

### Выход

```json
{
  "status": "refreshed",
  "cache_key": "rmd:392:948:ru",
  "fetched_at": "2026-03-29T12:00:00Z"
}
```

## Tool 9. `df_search_semantic_entities`

### Назначение

Ищет меры и измерения по имени, описанию, группе, блоку.

### Вход

```json
{
  "project_id": 392,
  "version_id": 948,
  "query": "доход клиент",
  "language": "ru",
  "limit": 20
}
```

### Выход

```json
{
  "matches": [
    {
      "entity_type": "measure",
      "name": "Общий доход",
      "group": "Продажи",
      "block": "Доход",
      "score": 0.92
    },
    {
      "entity_type": "dimension",
      "name": "ID клиента",
      "group": "Продажи",
      "block": "Клиент",
      "score": 0.88
    }
  ]
}
```

## Какие tools нужны в MVP обязательно

Обязательный набор:

- `df_health`
- `df_list_projects`
- `df_list_versions`
- `df_get_measures`
- `df_get_dimensions`
- `df_get_rmd`
- `df_refresh_cache`

## Какие tools можно добавить во второй релиз

- `df_get_semantic_summary`
- `df_search_semantic_entities`
- `df_get_entity_by_name`
- `df_get_groups`
- `df_get_blocks`

## Принципы ответа tools

Каждый tool должен:

- возвращать JSON-совместимую структуру
- иметь стабильную схему ответа
- не зависеть от конкретного MCP-клиента
- по возможности возвращать `stats`
- при ошибке возвращать нормализованный error object

## Формат ошибок

```json
{
  "error": {
    "code": "DATAFORGE_API_KEY_INVALID",
    "message": "Invalid API key",
    "details": {
      "http_status": 401
    }
  }
}
```
