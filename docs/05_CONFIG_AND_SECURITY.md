# 05. Config and Security

## Общий принцип

Хотя сервер не выполняет SQL, он все равно является чувствительным интеграционным компонентом.

Он получает доступ к семантическому слою DataForge через API key, а значит должен строиться как production-grade сервис.

## Какие секреты нужно хранить

Нужно отделить конфигурацию от секретов.

### Секреты

- `DATAFORGE_API_KEY`
- внутренние токены админ-доступа к самому MCP-серверу, если они используются

### Несекретные настройки

- `DATAFORGE_BASE_URL`
- `DEFAULT_LANGUAGE`
- `CACHE_DIR`
- `CACHE_TTL_SECONDS`
- `HOST`
- `PORT`
- `LOG_LEVEL`

## Пример `.env.example`

```env
DATAFORGE_BASE_URL=https://api.prod-df.businessqlik.com
DATAFORGE_API_KEY=replace_me
DEFAULT_LANGUAGE=ru

CACHE_BACKEND=file
CACHE_DIR=./cache
CACHE_TTL_SECONDS=3600

MCP_SERVER_NAME=dataforge-semantic
MCP_TRANSPORT=stdio

HOST=0.0.0.0
PORT=8080

LOG_LEVEL=INFO
```

## Почему нельзя хардкодить ключи

Ключ DataForge фактически дает доступ от имени пользователя.
Если он утечет, можно получить доступ к доступным этому пользователю проектам, версиям и RMD.

Поэтому:

- ключ нельзя хранить в git
- ключ нельзя класть в donor files
- ключ нельзя передавать в логах
- ключ нельзя возвращать через MCP tools

## Ротация ключей

Нужно заложить инструкцию на случай компрометации:

1. выпустить новый API key в DataForge
2. обновить секрет в окружении сервера
3. перезапустить сервис
4. убедиться, что старый ключ более не используется

## Нужно ли вводить свой auth на MCP-сервере

### Для stdio режима

Обычно нет, потому что доступ контролируется локальной машиной и настройками MCP-клиента.

### Для SSE режима

Да, желательно.
Иначе сервер может стать открытым прокси к Product API.

Минимум:
- `X-Internal-Api-Key` для входа на ваш MCP SSE endpoint
или
- reverse proxy auth
или
- private network only

## Cache policy

Кэш обязателен, но должен быть прозрачным.

Нужно поддержать:

- cache key по `(project_id, version_id, language, endpoint_type)`
- TTL
- принудительное обновление
- last-known-good fallback

### Рекомендуемые cache keys

- `projects:{page}:{page_size}`
- `versions:{project_id}:{page}:{page_size}`
- `measures:{project_id}:{version_id}:{language}`
- `dimensions:{project_id}:{version_id}:{language}`
- `rmd:{project_id}:{version_id}:{language}`

## Логирование

Логи должны быть структурированными.

Минимальные поля:

- timestamp
- request_id
- tool_name
- project_id
- version_id
- cache_hit
- response_time_ms
- http_status_to_dataforge
- error_code

Нельзя логировать:

- `DATAFORGE_API_KEY`
- полный raw response, если в нем появятся чувствительные поля
- конфигурацию окружения целиком

## Retry policy

Для Product API надо задать аккуратную retry policy.

Рекомендация:

- retry only for 5xx and network errors
- no retry for 401/403/404
- exponential backoff
- небольшое число повторов, например 2 или 3

## Timeout policy

Не нужно держать MCP client слишком долго.

Рекомендация:

- connect timeout: 5s
- read timeout: 30s
- full tool timeout: 45s

## Формат internal config class

Пример структуры:

```python
class Settings(BaseSettings):
    dataforge_base_url: str
    dataforge_api_key: SecretStr
    default_language: str = "ru"
    cache_backend: str = "file"
    cache_dir: str = "./cache"
    cache_ttl_seconds: int = 3600
    mcp_server_name: str = "dataforge-semantic"
    mcp_transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
```

## Файловый кэш в MVP

На первом этапе достаточно использовать файловый кэш.

Структура:

```text
cache/
├── projects/
├── versions/
├── measures/
├── dimensions/
└── rmd/
```

Каждый объект можно хранить как JSON плюс metadata file:

```json
{
  "fetched_at": "2026-03-29T12:00:00Z",
  "ttl_seconds": 3600,
  "payload": {}
}
```
