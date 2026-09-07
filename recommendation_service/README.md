# recommendation_service

gRPC-сервис рекомендаций мероприятий.

- gRPC-сервер (`grpc.aio`). Контракты — в общем корневом `proto/`,
  стабы генерируются в `src/grpc/generated/` (`python -m scripts.gen_proto`).
- При необходимости — свой доступ к данным (PostgreSQL).
- Вызывается из `api_service`.

Порт: `50051`. Переменные окружения — см. `.env.template`.

Общее описание монорепо и трейдоффы подхода — в корневом [`README.md`](../README.md).
