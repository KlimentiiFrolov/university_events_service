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

```text
.
├── .github/
│   └── pull_request_template.md
├── docs/
│   ├── course-assignment.pdf
│   ├── lab-00/
│   │   └── report.docx
│   ├── lab-01/
│   ├── lab-02/
│   ├── lab-03/
│   ├── lab-04/
│   ├── lab-05/
│   └── lab-06/
├── src/
│   ├── api_service/
│   ├── recommendation_service/
│   ├── notification_service/
│   ├── notification_client/
│   └── common/
├── proto/
├── migrations/
├── tests/
│   ├── unit/
│   └── integration/
├── infra/
│   ├── docker/
│   └── nginx/
├── scripts/
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
└── README.md
```

### Что где хранить

- `docs/` — задание по курсу, отчёты, схемы и материалы по каждой лабораторной.
- `src/api_service/` — основной FastAPI-сервис, REST API, авторизация, бизнес-логика и доступ к БД.
- `src/recommendation_service/` — отдельный gRPC-сервис рекомендаций.
- `src/notification_service/` — RabbitMQ consumer + WebSocket-сервис уведомлений.
- `src/notification_client/` — клиент, который получает уведомления по WebSocket.
- `src/common/` — общий код, который действительно нужен нескольким сервисам. Не складывать сюда всё подряд.
- `proto/` — `.proto`-контракты gRPC.
- `migrations/` — миграции Alembic.
- `tests/` — модульные и интеграционные тесты.
- `infra/` — инфраструктурные файлы Docker/Nginx.
- `scripts/` — вспомогательные команды и демонстрационные скрипты.

## Лабораторные работы

| ЛР | Содержание | Основные каталоги |
|---|---|---|
| 0 | ТЗ, предметная область, БД, архитектура | `docs/lab-00/` |
| 1 | PostgreSQL, SQLAlchemy, CRUD, тестовый скрипт, Alembic | `src/api_service/`, `migrations/`, `tests/`, `scripts/` |
| 2 | REST API, FastAPI, Pydantic, JWT, при необходимости Nginx | `src/api_service/`, `infra/nginx/`, `tests/` |
| 3 | gRPC-сервис рекомендаций | `src/recommendation_service/`, `proto/` |
| 4 | RabbitMQ, Notification Service, WebSocket-клиент | `src/notification_service/`, `src/notification_client/` |
| 5 | Docker и Docker Compose | `infra/docker/`, корневой `docker-compose.yml` |
| 6 | Дополнительный SSR-интерфейс на Jinja2 | внутри `src/api_service/` |

## Git workflow

Для проекта из двух человек отдельная постоянная ветка `develop` не нужна. Используем три уровня:

1. `main` — только завершённое и сдаваемое состояние.
2. `lab/N-name` — интеграционная ветка текущей лабораторной.
3. `feature/...`, `fix/...`, `docs/...`, `test/...` — короткие ветки конкретных задач.

Пример для ЛР №1:

```text
main
 └── lab/1-database
      ├── feature/sqlalchemy-models
      ├── feature/crud-repositories
      └── docs/lab-1-report
```

Feature-ветки вливаются Pull Request'ами в `lab/1-database`. Когда лабораторная готова целиком, делаем итоговый PR `lab/1-database -> main`. После merge ставим тег:

```bash
git switch main
git pull origin main
git tag -a lab-1 -m "Lab 1 completed"
git push origin lab-1
```

Рекомендуемые ветки лабораторных:

```text
lab/1-database
lab/2-rest-api
lab/3-grpc-recommendations
lab/4-notifications
lab/5-docker
lab/6-ssr
```

Подробная инструкция по созданию GitHub-репозитория, приглашению напарника и защите `main` находится в [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md).

## Стиль коммитов

Используем короткие понятные сообщения в стиле Conventional Commits:

```text
feat(db): add event and registration models
feat(api): add event creation endpoint
feat(grpc): implement recommendation service
fix(api): prevent registration over capacity
test(db): cover registration constraints
docs(lab1): add laboratory report
chore(docker): add compose configuration
```

Не стоит делать коммиты вроде `fix`, `new`, `lab`, `123`, `final_final`.

## Работа вдвоём

1. Перед началом работы обновить `main`.
2. Каждый работает в своей ветке.
3. Не пушить напрямую в `main`.
4. На каждую законченную задачу — небольшой логичный commit.
5. Перед merge — Pull Request и просмотр изменений напарником.
6. После сдачи лабораторной — тег `lab-N`.

## Секреты и настройки

Файл `.env` **не коммитится**. В репозитории хранится только `.env.example` без настоящих паролей и секретов.

Пример локальной настройки:

```bash
cp .env.example .env
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

Команды запуска будут добавляться по мере реализации лабораторных работ. К ЛР №5 весь проект должен запускаться одной командой:

```bash
docker compose up
```
