# Замечания по шлюзу после интеграции с DataForge Analyst Agent

**Дата:** 2026-09-23 · **Проверялось на коммите:** `0119e16` ·
**Стенд:** DataForge `https://<dataforge-host>` (API v2), Docker 29.7.2, Windows 11.

Шлюз поднимался в режиме `streamable-http` и проверялся живым клиентом
(DataForge Analyst Agent). Ниже — что мешало запуститься, что мешало работать и
что стоит доработать в API. Три механические правки уже сделаны в этой ветке,
остальное требует вашего участия.

---

## 1. Блокеры запуска

### 1.1. Пакета `dataforge_mcp.cache` нет в дистрибутиве — ИСПРАВИТЬ ВРУЧНУЮ

Строка `cache/` в `.gitignore` предназначена для рантайм-каталога кэша
(`CACHE_DIR=./cache`), но шаблон без ведущего слэша совпадает **с любым**
каталогом `cache` на любой глубине — в том числе с `src/dataforge_mcp/cache/`.

Последствия:

* в репозитории из этого каталога лежит только `store.py` (видимо, добавлен через
  `git add -f`), а `__init__.py` и `file_store.py` **не коммитились никогда**;
* hatchling уважает `.gitignore`, поэтому пакет не попадает в wheel;
* падает **любой** способ запуска, не только Docker:

```console
$ pip install "dataforge-mcp @ git+https://github.com/SGromych/dataforge-mcp-gateway.git"
$ python -m dataforge_mcp
ModuleNotFoundError: No module named 'dataforge_mcp.cache'
```

В Docker ошибка точнее, потому что `COPY src/ src/` приносит `store.py`:

```
File "/usr/local/lib/python3.11/site-packages/dataforge_mcp/__init__.py", line 19
    from dataforge_mcp.cache.file_store import FileCacheStore
ModuleNotFoundError: No module named 'dataforge_mcp.cache.file_store'
```

Что файл существует у вас локально, видно по `tests/test_cache.py` — он импортирует
`from dataforge_mcp.cache.file_store import FileCacheStore`.

**Правило `.gitignore` в этой ветке уже исправлено** (`cache/` → `/cache/`).
Осталось сделать у себя:

```bash
git add src/dataforge_mcp/cache/__init__.py src/dataforge_mcp/cache/file_store.py
git commit -m "Commit the cache package that .gitignore was swallowing"
```

Я намеренно **не** добавил эти два файла в ветку: у вас они есть в рабочей копии,
и коммит моей версии либо перетёр бы вашу реализацию, либо помешал переключению
ветки. Если файл всё же потерян — в приложении А лежит рабочая заглушка,
достаточная для запуска (без блокировок и без ограничения размера кэша).

**Как проверить, что починилось:**

```bash
git ls-files src/dataforge_mcp/cache/     # должны быть все три файла
pip install .                             # в чистом venv
python -c "import dataforge_mcp; print('ok')"
```

### 1.2. Docker-сборка падает на метаданных — ИСПРАВЛЕНО В ВЕТКЕ

`pyproject.toml` объявляет `readme = "README.md"`, а builder-стадия копирует только
`pyproject.toml` и `src/`:

```
OSError: Readme file does not exist: README.md
error: metadata-generation-failed
ERROR: process "/bin/sh -c pip install --no-cache-dir ." did not complete successfully
```

Добавлен `COPY README.md .`.

### 1.3. Незакреплённая версия `mcp` ломает сервер — ИСПРАВЛЕНО В ВЕТКЕ

Объявлено `mcp>=1.26` без верхней границы. Сегодня ставится **mcp 2.2.0**, где у
`mcp.server.Server` больше нет декораторов `list_tools()` / `call_tool()`:

```
File "/usr/local/lib/python3.11/site-packages/dataforge_mcp/mcp/tools.py", line 37
    @server.list_tools()
AttributeError: 'Server' object has no attribute 'list_tools'
```

Поставлено `mcp>=1.26,<2`. Проверено: с **1.30.0** шлюз стартует и работает.
Если планируется поддержка 2.x — это отдельная задача на `mcp/tools.py` и
`mcp/server.py`.

---

## 2. Что мешало работать (не блокеры, но грабли)

### 2.1. Базовый URL: шлюз не знает про префикс `/api`

Шлюз строит пути как `/df-api/v2/projects/...` (см. `dataforge/client.py`), что
верно для `api.prod-df.businessqlik.com`, где префикс зашит в хост. На нашем
инстансе API живёт под `/api/df-api/v2/...`, а на `/df-api/v2/...` отдаётся
HTML главной страницы SPA. Симптом:

```json
{"server_status":"ok","product_api_status":"unavailable", ...}
{"tool_name":"df_list_projects","error":"JSONDecodeError","event":"tool_failed"}
```

Рабочая настройка для такого деплоя:

```env
DATAFORGE_BASE_URL=https://<dataforge-host>/api
```

**Предложение:** упомянуть это в `docs/api/configuration.md` — что `DATAFORGE_BASE_URL`
должен указывать на корень **API**, а не на корень сайта, и что при неверном значении
симптом выглядит как `JSONDecodeError`, а не как 404.

### 2.2. Ошибки валидации приходят не в задекларированном формате

`docs/api/schemas.md` описывает структуру `{code, message, api_code, fields[], hint, …}`.
На практике ошибка валидации аргументов приходит простым текстом:

```json
{"content":[{"type":"text","text":"Input validation error: '18' is not of type 'integer'"}],
 "isError":true}
```

Клиент, написанный по документации, показывает пользователю «неизвестная ошибка».
**Предложение:** либо приводить такие ошибки к общей структуре, либо явно описать
в `schemas.md`, что ошибки валидации аргументов — это текст.

### 2.3. Строгая типизация идентификаторов

Схемы инструментов объявляют `project_id` / `version_id` / `data_mart_id` как
`integer`, и строка `"18"` отклоняется. Это законно, но стоит заметности: у многих
клиентов идентификаторы хранятся строками (у нас — в профиле подключения).
**Предложение:** либо принимать `["integer","string"]` с приведением, либо вынести
это в README как отдельный пункт.

---

## 3. Доработка API: витрины не говорят, где они лежат

Самое полезное для нас изменение.

Ответ `GET /data-marts/{id}/view` выглядит так:

```json
{"exists": true, "type": "Table", "database": "clickhouse", "schema": null,
 "name": "table_<id>_datamart_<name>", "status": "active", "is_stale": false,
 "last_refresh_at": "2026-07-06T14:12:35.475Z",
 "connection": {"id": "<id>", "name": "<исходное подключение>", "db_type": "clickhouse"}}
```

Здесь **нет ответа на вопрос «в какой базе лежит таблица»**:

* `database` содержит **тип СУБД** (`"clickhouse"`), а не имя базы;
* `schema` приходит `null`;
* `connection` указывает на **исходное** подключение, а не на приёмник.

А приёмник — другой. Мы это видим на данных: витрина одной модели
`table_<id>_datamart_<name>` (12 491 строка) физически лежит в базе
**`<mart-store-db>`**, хотя источник — `<source-db>`. Актуальные версии проекта
объявляют вторым подключением «Test DB» → `<internal-mart-db>`, и трёх заявленных витрин
в доступных нам базах нет вовсе:

```sql
SELECT count() FROM <source-db>.`table_<id>_datamart_<name>`;
-- Code: 60. Unknown table expression identifier
SELECT count() FROM <mart-store-db>.`table_<other-id>_datamart_<name>`;
-- 3406089
```

(права у нашего пользователя на чтение обеих баз полные, так что это не
вопрос видимости — таблицы действительно нет в базе источника.)

**Просьба:** добавить в ответ `view` реальное размещение — например
`target_connection_id`, `target_database`, `target_schema`. Тогда клиент сможет
обратиться к витрине напрямую, а не перебирать схемы в поисках таблицы.

**И вопрос:** где на самом деле материализуются эти витрины? Если в
`<internal-mart-db>` — нам нужен доступ на чтение:

```sql
GRANT SHOW TABLES, SELECT ON <internal-mart-db>.* TO <db-user>;
```

---

## 4. Мелочи

* `docker-compose.yml` не задаёт `MCP_AUTH_TOKEN` (он закомментирован), при этом
  порт публикуется на `0.0.0.0`. С учётом 41 изменяющего инструмента лучше сделать
  токен обязательным при не-loopback биндинге — сейчас это только предупреждение
  в логе.
* На Windows/Git Bash `-e MCP_HTTP_PATH=/mcp` превращается в
  `/C:/Program Files/Git/mcp` из-за конвертации путей MSYS. Лечится
  `MSYS_NO_PATHCONV=1`. Стоит строчки в README — симптом неочевидный: сервер
  стартует «успешно», но эндпоинта по `/mcp` нет.
* `docker/healthcheck.py` и `/health` работают корректно, контейнер переходит в
  `healthy` — здесь всё хорошо.

---

## 5. Что уже проверено и работает

После трёх правок (1.1 вручную + 1.2 и 1.3 из этой ветки) шлюз поднимается и
полностью отрабатывает. Клиент прошёл:

| Проверка | Результат |
|---|---|
| `df_health` | `server_status: ok`, `product_api_status: ok` |
| `df_list_projects` / `df_list_versions` | все проекты и версии на месте |
| `df_get_measures` против прямого REST | **14 = 14, состав совпал посимвольно** |
| `df_get_dimensions` / `df_get_facts` | 26 и 6 — как по REST |
| `df_list_data_marts` / `df_get_data_mart_view` | витрина и статус вьюхи читаются |
| `df_list_fact_tables` / `df_list_relationships` | 2 и 8 |
| `df_generate_sql` | отдаёт корректный ClickHouse-SQL, `validation_errors: []` |
| Bearer-авторизация | без токена 401, с неверным — 401 |
| Сессии `Mcp-Session-Id` | initialize → session → tools/call работают |

Замечание по протоколу для других клиентов: сервер отвечает **400 Bad Request**,
если в заголовке `MCP-Protocol-Version` прислать не ту версию, что была
согласована на `initialize` (он отвечает `2025-11-25`). Это соответствует
спецификации, но ошибка не поясняется — стоит вернуть текст.

---

## Приложение А. Заглушка `src/dataforge_mcp/cache/file_store.py`

Нужна, только если ваш файл потерян. Реализует контракт `CacheStore` из
`store.py`; для продакшена сыровата (нет блокировок и ограничения размера).

```python
"""File-based cache store."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dataforge_mcp.cache.store import CacheEntry, CacheStore


class FileCacheStore(CacheStore):
    def __init__(self, cache_dir: str = "./cache") -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self._dir / f"{digest}.json"

    def _read(self, key: str) -> tuple[CacheEntry, Path] | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return CacheEntry(**json.loads(path.read_text(encoding="utf-8"))), path
        except Exception:
            return None

    async def get(self, key: str) -> Any | None:
        found = self._read(key)
        if not found:
            return None
        entry, _ = found
        fetched = entry.fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > timedelta(seconds=entry.ttl_seconds):
            return None
        return entry.payload

    async def get_last_known_good(self, key: str) -> Any | None:
        found = self._read(key)
        return found[0].payload if found else None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        entry = CacheEntry(fetched_at=datetime.now(timezone.utc), ttl_seconds=ttl, payload=value)
        self._path(key).write_text(entry.model_dump_json(), encoding="utf-8")
        index = self._dir / "index.json"
        try:
            data = json.loads(index.read_text(encoding="utf-8")) if index.exists() else {}
        except Exception:
            data = {}
        data[key] = self._path(key).name
        index.write_text(json.dumps(data), encoding="utf-8")

    async def invalidate(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    async def invalidate_prefix(self, prefix: str) -> int:
        index = self._dir / "index.json"
        if not index.exists():
            return 0
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except Exception:
            return 0
        removed = 0
        for key in [k for k in data if k.startswith(prefix)]:
            path = self._dir / data.pop(key)
            if path.exists():
                path.unlink()
            removed += 1
        index.write_text(json.dumps(data), encoding="utf-8")
        return removed

    async def is_healthy(self) -> bool:
        try:
            probe = self._dir / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except Exception:
            return False
```

`src/dataforge_mcp/cache/__init__.py` может быть пустым.

---

## Приложение Б. Как воспроизвести проверку

```bash
git checkout fix/packaging-and-build
git add src/dataforge_mcp/cache/__init__.py src/dataforge_mcp/cache/file_store.py

docker build -t dataforge-mcp:local .

# Windows/Git Bash: MSYS_NO_PATHCONV=1 обязателен, иначе /mcp станет путём
MSYS_NO_PATHCONV=1 docker run -d --name dfmcp -p 8080:8080 \
  -e MCP_TRANSPORT=streamable-http -e HOST=0.0.0.0 -e PORT=8080 -e MCP_HTTP_PATH=/mcp \
  -e MCP_AUTH_TOKEN=<token> \
  -e DATAFORGE_BASE_URL=https://<dataforge-host>/api \
  -e DATAFORGE_API_KEY=<key> \
  dataforge-mcp:local

curl http://localhost:8080/health          # {"status":"ok"}
docker logs dfmcp | grep mcp_transport_starting   # path должен быть "/mcp"
```
