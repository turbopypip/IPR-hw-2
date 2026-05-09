# Описание
Домашнее задание по FastAPI в рамках курса "Прикладной Python"
# API для сервиса сокращения ссылок – shortist


## Описание API

Этот сервис предоставляет REST API для:
- Аутентификации пользователей (регистрация, вход, выход)
- Создания, управления и отслеживания сокращенных ссылок
- Получения статистики по ссылкам

API разделен на две основные группы эндпоинтов:
- `/auth` - для работы с пользователями
- `/links` - для работы со ссылками

## Примеры запросов

### Аутентификация

#### Регистрация нового пользователя
```http
POST /auth/register

{
  "email": "user@example.com",
  "password": "string",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false
}
```

#### Вход пользователя
```http
POST /auth/jwt/login
grant_type=password&username=username@example.com&password=password
```

#### Выход пользователя
```http
POST /auth/jwt/logout
```

### Работа со ссылками
#### Создание сокращенной ссылки
```http
POST /links/shorten

{
"original_url": "https://example.com",
"custom_alias": "my-link",
"expire_at": "2025-04-30T22:30+00:00"
}
```
#### Получение оригинальной ссылки (редирект)
```http
GET /links/{short_id}
```

#### Получение статистики по ссылке
```http
GET /links/{short_id}/stats
```

#### Обновление ссылки
```http
PUT /links/{short_id}

{
"original_url": "https://new-example.com",
"expire_at": "2025-05-30T22:30+00:00"
}
```


#### Удаление ссылки
```http
DELETE /links/{short_id}
```

#### Поиск ссылок
```http
GET /links/search/?original_url=http://example.com
```


### Инструкция по запуску

- Создайте и наполните .env файл под вашу конфигурацию
- Запустите сборку контейнеров: `docker-compose up -d --build`
- Выполните миграцию с инициализацией БД по схеме проекта: `docker-compose exec web alembic upgrade head`

### Запуск тестов и проверка покрытия

Проект рассчитан на PostgreSQL, поэтому тесты также запускаются с отдельной PostgreSQL-базой. Не используйте рабочую базу для тестов: фикстуры создают и очищают таблицы в базе, указанной в `TEST_DATABASE_URL`.

Полный пример запуска тестов и проверки покрытия:

```bash
cd /Users/deniskockin/progs/IPR/dz2/shortist

docker start shortist-test-postgres || docker run --name shortist-test-postgres \
  -e POSTGRES_DB=shortist_test \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -p 55432:5432 \
  -d postgres:15

until docker exec shortist-test-postgres pg_isready -U test -d shortist_test; do sleep 1; done

export DB_USER=test
export DB_PASS=test
export DB_HOST=localhost
export DB_PORT=55432
export DB_NAME=shortist_test
export SECRET=test-secret
export TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:55432/shortist_test

python3 -m pip install -r requirements.txt

coverage erase
coverage run -m pytest tests -ra
coverage report -m
coverage html
```

После команды `coverage html` отчет будет доступен в `htmlcov/index.html`. На macOS его можно открыть командой:

```bash
open htmlcov/index.html
```

Альтернативно можно запустить сразу через `pytest-cov`:

```bash
pytest --cov=src --cov-report=term-missing --cov-report=html tests
```

После проверки контейнер с тестовой базой можно остановить:

```bash
docker rm -f shortist-test-postgres
```

### Нагрузочное тестирование

Для нагрузки используется `Locust`. Нагрузочные тесты проверяют массовое создание коротких ссылок:
- `POST /links/shorten` без кастомного алиаса;
- `POST /links/shorten` с `custom_alias`.

Каждый запрос считается успешным только если API вернул статус `200` и поле `short_id`.

Перед запуском нагрузки поднимите тестовую БД, задайте переменные окружения и создайте таблицы:

```bash
cd /Users/deniskockin/progs/IPR/dz2/shortist

docker start shortist-test-postgres || docker run --name shortist-test-postgres \
  -e POSTGRES_DB=shortist_test \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -p 55432:5432 \
  -d postgres:15

until docker exec shortist-test-postgres pg_isready -U test -d shortist_test; do sleep 1; done

export DB_USER=test
export DB_PASS=test
export DB_HOST=localhost
export DB_PORT=55432
export DB_NAME=shortist_test
export SECRET=test-secret

python3 - <<'PY'
import asyncio
from src.database import Base, async_engine
from src.auth.models import User
from src.links.models import Link

async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(main())
PY
```

Запустите сервис в отдельном терминале:

```bash
python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

После этого можно запускать нагрузочные тесты. Smoke-прогон проверяет, что сценарии нагрузки работают:

```bash
bash scripts/run_load_tests.sh smoke
```

Ступенчатый прогон помогает увидеть, при каком числе виртуальных пользователей начинают расти задержки или ошибки:

```bash
bash scripts/run_load_tests.sh stepped
```

Можно запустить оба набора подряд:

```bash
bash scripts/run_load_tests.sh all
```

Отчеты сохраняются в папку `load_reports/` с подпапками по типу теста и дате запуска:

```text
load_reports/
  smoke/
    2026-05-09_15-10-00/
      users_5/
        console.log
        locust.html
        locust_stats.csv
        locust_stats_history.csv
        locust_failures.csv
        locust_exceptions.csv
        run_info.txt
  stepped/
    2026-05-09_15-10-00/
      users_10/
      users_25/
      users_50/
      users_100/
```

Папка `load_reports/` генерируется автоматически и не добавляется в git.
