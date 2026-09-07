# api_service

Основной FastAPI-сервис: каталог мероприятий, регистрация участников, работа
организатора, авторизация (JWT), при необходимости SSR-интерфейс на Jinja2.

- REST API + бизнес-логика + доступ к PostgreSQL (SQLAlchemy, Alembic).
- Публикует события в RabbitMQ для `notification_service`.
- Ходит в `recommendation_service` по gRPC.

Порт: `8000`. Переменные окружения — см. `.env.template`.

Общее описание монорепо и трейдоффы подхода — в корневом [`README.md`](../README.md).
