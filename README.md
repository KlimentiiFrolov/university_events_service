# Сервис регистрации на университетские мероприятия

Учебный проект по курсу **«Технологии сетевого программирования»**.

Проект развивается поэтапно в рамках лабораторных работ. Предметная область — регистрация пользователей на университетские мероприятия: каталог событий, запись участников, работа организатора, рекомендации и уведомления в реальном времени.

## Команда

- Георгий Зазуля
- Климентий Фролов

## Планируемый стек

- Python
- PostgreSQL
- SQLAlchemy
- FastAPI
- Pydantic
- JWT
- gRPC + Protocol Buffers
- RabbitMQ
- WebSocket
- Docker + Docker Compose
- Jinja2 — для дополнительной лабораторной работы с SSR

## Структура репозитория

Корень репозитория тонкий: единственный файл оркестрации `docker-compose.yml`, документация и по одной папке на микросервис. Каждая папка-сервис **самодостаточна** и повторяет структуру примера `Session_Auth` (свой `src/`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `.env.template`, свой `alembic/` там, где нужна БД).

```text
.
├── docker-compose.yml          # единственная точка оркестрации
├── README.md
├── docs/                       # задание по курсу отчёты по лабораторным
│   ├── course-assignment.pdf
│   └── lab-00 … lab-06/
├── scripts/                    # вспомогательные и демонстрационные скрипты
│
├── api_service/                # FastAPI: каталог, регистрация, авторизация, SSR
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.template
│   ├── src/
│   └── tests/
│
├── recommendation_service/     # gRPC-сервис рекомендаций
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.template
│   ├── src/
│   └── tests/
│
├── notification_service/       # RabbitMQ consumer + WebSocket
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.template
│   ├── src/
│   └── tests/
│
└── notification_client/        # клиент уведомлений по WebSocket
    ├── Dockerfile
    ├── pyproject.toml
    ├── .env.template
    ├── src/
    └── tests/
```

### Что где хранить

- `docs/` — задание по курсу, отчёты, схемы и материалы по каждой лабораторной.
- `<service>/src/` — код сервиса. Внутренняя раскладка — по образцу `Session_Auth`:
  `core/` (конфиг, БД, логгер, безопасность), `api/` или `grpc/` (транспортный слой),
  `services/` (бизнес-логика), `repositories/` (доступ к данным), `models/`, `schemas/`,
  `alembic/` (миграции). Появляется по мере реализации лабораторных.
- `<service>/tests/` — модульные и интеграционные тесты сервиса.
- `<service>/.env.template` — значения окружения по умолчанию (коммитится);
  реальный `.env` не коммитится.
- `<service>/Dockerfile` — образ сервиса, контекст сборки — папка самого сервиса.
- корневой `docker-compose.yml` — поднимает инфраструктуру (PostgreSQL, Redis, RabbitMQ)
  и все сервисы.

### Планируемая внутренняя структура сервисов

Ниже — ориентир, к которому идёт каждый сервис. На старте внутри `src/` пусто.

- **api_service** — `core/`, `api/` (роутеры: `events`, `registrations`, `auth`, `organizer`),
  `services/`, `repositories/`, `models/` (+ `mixins/`), `schemas/` (+ `exceptions/`),
  `clients/` (gRPC-клиент рекомендаций, publisher в RabbitMQ), `alembic/`, `ssr/templates/`.
- **recommendation_service** — `core/`, `grpc/` (реализация сервисера + сгенерированные стабы),
  `services/`, `repositories/`, `models/`, `schemas/`, `proto/`, `alembic/`.
- **notification_service** — `core/`, `consumers/` (обработчики очередей RabbitMQ),
  `websocket/` (эндпоинты, менеджер подключений), `services/`, `schemas/`.
- **notification_client** — `core/`, точка входа `main.py`.

## Архитектура: почему так и какие трейдоффы

Выбрана плоская раскладка «папка на микросервис + один `docker-compose.yml`». Общего Python-пакета нет: совпадающий код (конфиг, логгер, обёртки над БД/RabbitMQ, контракты событий и `.proto`) сознательно дублируется между сервисами.

### Плюсы

- **Чистое разделение ответственности.** Логика одного сервиса физически не может обратиться к другому напрямую — только через REST / gRPC / очередь. Это ровно то, что проверяется в курсе.
- **Независимые зависимости и релизы.** У каждого сервиса свой `pyproject.toml` / `uv.lock`; обновление библиотеки в одном сервисе не задевает остальные.
- **Простой и быстрый Docker-билд.** Контекст сборки маленький, кэш слоёв не инвалидируется из-за изменений в соседнем сервисе. Dockerfile — почти копия рабочего из `Session_Auth`.
- **Низкий порог входа.** Каждая папка — знакомый по `Session_Auth` проект; можно открыть один сервис и работать, не держа в голове весь монорепо.
- **Лёгкий вынос в отдельный репозиторий** позже — папка уже самодостаточна.

### Минусы

- **Дрейф дублированного кода.** Исправление в `core/` одного сервиса не попадает автоматически в остальные; «одинаковые» файлы со временем расходятся.
- **Контракты не проверяются на этапе импорта.** Схема события или `.proto` лежит в двух местах — рассинхрон ловится только тестами/рантаймом. Нужна дисциплина: менять обе копии в одном PR.
- **Нет сборки и линтинга «одной командой».** `ruff`, `pytest`, `uv sync` запускаются в каждой папке (или через скрипт-обёртку в `scripts/`).
- **Дублирование окружения.** Общие параметры (Postgres, RabbitMQ) повторяются в нескольких `.env.template`; при смене — править везде.
- **Больше boilerplate на старте** — по `Dockerfile`, `pyproject.toml` и `core/` на каждый сервис.

### Средний путь, если дублирование начнёт мешать

Оставить ту же плоскую раскладку, но вынести `.proto` в общий верхнеуровневый `proto/` и генерировать стабы в каждый сервис скриптом. Небольшие общие модули (`config` / `logger` / `db`, ~150 строк) можно осознанно оставить дублированными — это дёшево и стабильно.

## Лабораторные работы

| ЛР | Содержание | Основные каталоги |
| --- | --- | --- |
| 0 | ТЗ, предметная область, БД, архитектура | `docs/lab-00/` |
| 1 | PostgreSQL, SQLAlchemy, CRUD, тестовый скрипт, Alembic | `api_service/`, `scripts/` |
| 2 | REST API, FastAPI, Pydantic, JWT, при необходимости Nginx | `api_service/` |
| 3 | gRPC-сервис рекомендаций | `recommendation_service/` |
| 4 | RabbitMQ, Notification Service, WebSocket-клиент | `notification_service/`, `notification_client/` |
| 5 | Docker и Docker Compose | все сервисы, корневой `docker-compose.yml` |
| 6 | Дополнительный SSR-интерфейс на Jinja2 | `api_service/` |

## Git workflow

Для проекта из двух человек отдельная постоянная ветка `develop` не нужна. Используем три уровня:

1. `main` — только завершённое и сдаваемое состояние.
2. `lab/N-name` — интеграционная ветка текущей лабораторной.
3. `feature/...`, `fix/...`, `docs/...`, `test/...` — короткие ветки конкретных задач.

Feature-ветки вливаются Pull Request'ами в ветку лабораторной. Когда лабораторная готова целиком — итоговый PR `lab/N-name -> main`, после merge ставим тег:

```bash
git switch main
git pull origin main
git tag -a lab-1 -m "Lab 1 completed"
git push origin lab-1
```

## Стиль коммитов

Короткие сообщения в стиле Conventional Commits:

```text
feat(api): add event creation endpoint
feat(grpc): implement recommendation service
fix(api): prevent registration over capacity
test(db): cover registration constraints
docs(lab1): add laboratory report
chore(docker): add compose configuration
```

## Секреты и настройки

Реальные `.env` не коммитятся. В репозитории хранится только `.env.template` каждого сервиса без настоящих паролей.

```bash
cp api_service/.env.template api_service/.env
```

## Текущее состояние

- [x] ЛР №0 — техническое задание и проектирование
- [ ] ЛР №1 — слой доступа к данным
- [ ] ЛР №2 — REST API
- [ ] ЛР №3 — gRPC
- [ ] ЛР №4 — RabbitMQ + WebSocket
- [ ] ЛР №5 — Docker Compose
- [ ] ЛР №6 — SSR/Jinja2 (дополнительная)

## Запуск

К ЛР №5 весь проект запускается одной командой:

```bash
docker compose up --build
```
