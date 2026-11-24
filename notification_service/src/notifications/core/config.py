import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/notifications/core/config.py -> корень notification_service
SERVICE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = SERVICE_DIR / ".env"
ENV_TEMPLATE = SERVICE_DIR / ".env.template"

ENV_CONFIG = SettingsConfigDict(
    env_file=(ENV_TEMPLATE, ENV_FILE),
    case_sensitive=False,
    extra="ignore",
)


class RuntimeSettings(BaseSettings):
    model_config = ENV_CONFIG

    host: Annotated[str, Field(default="0.0.0.0", alias="NOTIFICATION_HOST")]
    port: Annotated[int, Field(default=8001, alias="NOTIFICATION_PORT")]


class LoggerSettings(BaseModel):
    LOG_DEFAULT_FORMAT: str = "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
    level: int = logging.INFO
    datefmt: str = "%Y-%m-%d %H:%M:%S"


class RabbitMQSettings(BaseSettings):
    model_config = ENV_CONFIG

    rabbit_protocol: str = "amqp"
    rabbit_host: Annotated[str, Field(alias="RABBITMQ_HOST")]
    rabbit_port: Annotated[int, Field(alias="RABBITMQ_PORT")]
    rabbit_user: Annotated[str, Field(alias="RABBITMQ_USER")]
    rabbit_password: Annotated[str, Field(alias="RABBITMQ_PASSWORD")]
    exchange: Annotated[str, Field(default="university.events", alias="RABBITMQ_EXCHANGE")]
    queue: Annotated[str, Field(default="notifications", alias="NOTIFICATION_QUEUE")]
    # Какие события api_service нужны сервису уведомлений
    routing_keys: Annotated[
        list[str],
        Field(default=["registration.*", "event.*"], alias="NOTIFICATION_ROUTING_KEYS"),
    ]
    # Сколько неподтверждённых сообщений брокер отдаёт consumer'у одновременно
    prefetch_count: Annotated[int, Field(default=10, ge=1, alias="NOTIFICATION_PREFETCH_COUNT")]

    @property
    def dead_letter_exchange(self) -> str:
        return f"{self.queue}.dlx"

    @property
    def dead_letter_queue(self) -> str:
        return f"{self.queue}.dlq"

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"{self.rabbit_protocol}://{self.rabbit_user}:{self.rabbit_password}@"
            f"{self.rabbit_host}:{self.rabbit_port}"
        )


class DatabaseSettings(BaseSettings):
    """БД уведомлений. Префикс NOTIFICATIONS_DB_, а не POSTGRES_: в режиме embedded
    пакет работает в процессе api_service, где POSTGRES_* указывают на основную БД."""

    model_config = ENV_CONFIG

    db_name: Annotated[str, Field(alias="NOTIFICATIONS_DB_NAME")]
    db_user: Annotated[str, Field(alias="NOTIFICATIONS_DB_USER")]
    db_password: Annotated[str, Field(alias="NOTIFICATIONS_DB_PASSWORD")]
    db_host: Annotated[str, Field(alias="NOTIFICATIONS_DB_HOST")]
    db_port: Annotated[int, Field(alias="NOTIFICATIONS_DB_PORT")]
    db_echo: bool = False

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


class AuthSettings(BaseSettings):
    """Те же JWT_SECRET и JWT_ALGORITHM, что у api_service: сервис только проверяет токены."""

    model_config = ENV_CONFIG

    secret_key: Annotated[str, Field(alias="JWT_SECRET")]
    algorithm: Annotated[str, Field(alias="JWT_ALGORITHM")]
    # Срок жизни одноразового тикета на подключение к WebSocket
    ws_ticket_ttl_seconds: Annotated[int, Field(default=60, gt=0, alias="WS_TICKET_TTL_SECONDS")]


class Settings(BaseSettings):
    model_config = ENV_CONFIG

    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)  # type: ignore
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)  # type: ignore
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore
    auth: AuthSettings = Field(default_factory=AuthSettings)  # type: ignore

    log: LoggerSettings = LoggerSettings()


settings = Settings()
