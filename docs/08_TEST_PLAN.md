# 08. Test Plan

## Что нужно протестировать

Так как продукт работает только с семантическим API DataForge, тест-план должен закрывать четыре области:

- Product API client
- normalization
- cache
- MCP tools

## 1. Client tests

### Проверка `get_projects`

Должно быть покрыто:
- успешный ответ 200
- пагинация
- пустой список
- 401 invalid key
- 404 not found
- timeout
- retry for 5xx

### Проверка `get_versions`

Должно быть покрыто:
- корректный project id
- project without versions
- pagination handling

### Проверка `get_measures` / `get_dimensions` / `get_rmd`

Должно быть покрыто:
- корректный JSON
- корректный `language`
- поля присутствуют
- неизвестные поля не ломают парсер
- ошибки маппятся правильно

## 2. Normalizer tests

### Measures

Проверить:
- `measure_name` -> `name`
- `measure_description` -> `description`
- `connected_source` не теряется
- `raw` сохраняется
- nullable поля обрабатываются

### Dimensions

Проверить:
- `dimension_name` -> `name`
- `dimension_description` -> `description`
- `dimension_group` сохраняется
- `value_options` сохраняется

### Semantic summary

Проверить:
- группировка по `group`
- группировка по `block`
- сокращенный ответ без потери структуры

## 3. Cache tests

Проверить:
- запись в кэш
- чтение из кэша
- TTL expired
- force refresh
- corrupted cache file
- last-known-good fallback

## 4. MCP tools tests

Нужно проверить каждый tool отдельно.

### `df_health`

- server ok
- Product API unavailable
- cache unavailable

### `df_list_projects`

- возвращает projects
- pagination возвращается корректно

### `df_list_versions`

- требует `project_id`
- возвращает список версий

### `df_get_measures`

- требует `project_id` и `version_id`
- возвращает нормализованные measures

### `df_get_dimensions`

- требует `project_id` и `version_id`
- возвращает нормализованные dimensions

### `df_get_rmd`

- возвращает measures + dimensions + stats

### `df_refresh_cache`

- обновляет кэш
- меняет `fetched_at`

## 5. Integration tests

Нужен хотя бы один end-to-end сценарий:

1. поднять сервер
2. вызвать `df_list_projects`
3. выбрать проект
4. вызвать `df_list_versions`
5. вызвать `df_get_rmd`
6. убедиться, что ответ нормализован

## 6. Smoke tests against real DataForge

Перед релизом нужен реальный smoke test с валидным API key.

Проверить:
- облачный URL
- on-prem URL
- language=`ru`
- language=`en`
- large RMD
- cache refresh

## Что не надо тестировать сейчас

Не надо тратить время на тесты того, чего нет в scope:

- SQL execution
- database pool
- query timeout to DWH
- schema introspection
- text-to-sql
