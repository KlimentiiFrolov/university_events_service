# api_service

Основной FastAPI-сервис: каталог мероприятий, регистрация участников, работа
организатора, авторизация (JWT), при необходимости SSR-интерфейс на Jinja2.

- REST API + бизнес-логика + доступ к PostgreSQL (SQLAlchemy, Alembic).
- Публикует события в RabbitMQ для `notification_service`.
- Ходит в `recommendation_service` по gRPC.

Порт: `8000`. Переменные окружения — см. `.env.template`.

Общее описание монорепо и трейдоффы подхода — в корневом [`README.md`](../README.md).

# Работа с миграциями

1. Перейти в папку api_service

```cli
cd api_service
```

2. Если добавляется новая сущность в models, то надо обязательно импортировать его в  \_\_init\_\_.py того же модуля.

3. Чтобы сгенерировать миграцию в корне /api_service вводим

```cli
alembic revision --autogenerate -m <название миграции>
```

4. Накатить миграцию следующим образом 

```cli
alembic upgrade head
```

5. Откатить миграцию следующим образом 

```cli
alembic downgrade -1 (или head)
```

6. Если не хочется накатывать миграции локально, меняя POSTGRES_HOST на localhost, то используем следующие команды

```cli
docker compose exec app sh -c "uv run alembic upgrade head" 
```