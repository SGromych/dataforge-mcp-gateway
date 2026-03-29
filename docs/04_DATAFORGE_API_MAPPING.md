# 04. DataForge API Mapping

## Исходные эндпоинты Product API

Сервер должен работать поверх следующих DataForge RMD endpoints:

- `GET /rmd-api/v1/projects`
- `GET /rmd-api/v1/projects/{projectId}/versions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/measures`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd`

Все запросы должны отправляться с заголовком:

```http
X-Api-Key: <DATAFORGE_API_KEY>
```

## Base URL

Base URL должен задаваться конфигурацией.

Варианты:

- on-prem: `https://<YOUR_SERVER_HOST>`
- cloud: `https://api.prod-df.businessqlik.com`

## Таблица маппинга

### MCP: `df_list_projects`

DataForge API:

```http
GET {base_url}/rmd-api/v1/projects?page={page}&pageSize={page_size}
```

### MCP: `df_list_versions`

DataForge API:

```http
GET {base_url}/rmd-api/v1/projects/{project_id}/versions?page={page}&pageSize={page_size}
```

### MCP: `df_get_measures`

DataForge API:

```http
GET {base_url}/rmd-api/v1/projects/{project_id}/versions/{version_id}/measures?language={language}
```

### MCP: `df_get_dimensions`

DataForge API:

```http
GET {base_url}/rmd-api/v1/projects/{project_id}/versions/{version_id}/dimensions?language={language}
```

### MCP: `df_get_rmd`

DataForge API:

```http
GET {base_url}/rmd-api/v1/projects/{project_id}/versions/{version_id}/rmd?language={language}
```

## Особенности responses

### Projects

Ожидаемый ответ:

```json
{
  "projects": [
    {
      "id": 1,
      "name": "Название проекта",
      "description": "Описание проекта"
    }
  ],
  "pagination": {
    "total": 10,
    "page": 1,
    "pageSize": 10,
    "totalPages": 1
  }
}
```

### Versions

Ожидаемый ответ:

```json
{
  "versions": [
    {
      "id": 1,
      "name": "Название версии",
      "is_global": true
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "pageSize": 5,
    "totalPages": 1
  }
}
```

### Measures

Важно сохранять все смысловые поля measures, включая:

- `group`
- `block`
- `measure_name`
- `measure_description`
- `original_source_type`
- `original_source`
- `original_object`
- `data_type`
- `measure_type`
- `restrictions`
- `formula`
- `connected_source`
- `report_for_verification`
- `comment`
- `status`
- `relevance`
- `required`
- `visibility`
- `responsible_for_data`
- `variation`

### Dimensions

Важно сохранять все смысловые поля dimensions, включая:

- `group`
- `block`
- `dimension_name`
- `dimension_description`
- `original_source_type`
- `original_source`
- `original_object`
- `dimension_group`
- `data_type`
- `connected_source`
- `comment`
- `value_options`
- `status`
- `relevance`
- `required`
- `visibility`
- `responsible_for_data`

## Нормализация имен полей

Внутри сервера нужно использовать единый стиль.

### Measures

Из Product API:

- `measure_name` -> `name`
- `measure_description` -> `description`

### Dimensions

Из Product API:

- `dimension_name` -> `name`
- `dimension_description` -> `description`

### Общие поля

Сохранять как есть:

- `group`
- `block`
- `data_type`
- `status`
- `relevance`
- `required`
- `visibility`
- `responsible_for_data`
- `connected_source`

## Политика работы с `raw`

При нормализации рекомендуется сохранять исходный JSON целиком в поле `raw`.

Это позволит:

- не потерять данные при расширении схемы API
- быстро дебажить несоответствия
- делать backward-compatible evolution

Пример:

```json
{
  "name": "Общий доход",
  "description": "Общий доход от всех продаж",
  "group": "Продажи",
  "block": "Доход",
  "raw": {
    "...": "..."
  }
}
```

## Работа с пагинацией

Хотя endpoints поддерживают `page` и `pageSize`, для MCP лучше реализовать два режима.

### Режим 1. Pass-through

Сервер возвращает одну страницу и прокидывает pagination.

### Режим 2. Full fetch

Сервер сам забирает все страницы и возвращает агрегированный результат.

Для MVP рекомендую:

- `df_list_projects` и `df_list_versions` — поддерживать pass-through
- `df_get_measures`, `df_get_dimensions`, `df_get_rmd` — по умолчанию забирать полный набор

## Обработка ошибок DataForge API

Нужно явно картировать ошибки Product API в нормализованные коды сервера.

### 401 API_KEY.KEY_MISSING

Код сервера:

- `DATAFORGE_API_KEY_MISSING`

### 401 API_KEY.INVALID_KEY

Код сервера:

- `DATAFORGE_API_KEY_INVALID`

### 401 Unauthorized

Код сервера:

- `DATAFORGE_UNAUTHORIZED`

### 401 API_KEY.AUTH_FAILED

Код сервера:

- `DATAFORGE_AUTH_FAILED`

### 404 Not Found

Код сервера:

- `DATAFORGE_RESOURCE_NOT_FOUND`
