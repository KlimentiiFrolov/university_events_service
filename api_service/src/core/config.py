import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CERTS_PATH = BASE_DIR / "core" / "auth" / "certs"
ENV_FILE = BASE_DIR.parent / ".env"
ENV_TEMPLATE = BASE_DIR.parent / ".env.template"


class RuntimeSettings(BaseModel):
    host: Annotated[str, Field(default="0.0.0.0", alias="API_HOST")]
    port: Annotated[int, Field(default=8000, alias="API_PORT")]
    reload: bool = True


class LoggerSettings(BaseModel):
    LOG_DEFAULT_FORMAT: str = "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
    level: int = logging.INFO
    datefmt: str = "%Y-%m-%d %H:%M:%S"


class AuthSettings(BaseModel):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )
    private_key: Path = CERTS_PATH / "jwt-private.pem" # для подписывания токенов (создания)
    public_key: Path = CERTS_PATH / "jwt-public.pem" # для декодирования токенов
    algorithm: Annotated[str, Field(default="RS256", alias="JWT_ALGORITHM")]
    access_token_expire_minutes: Annotated[int, Field(default=15, alias="JWT_ACCESS_TTL_MINUTES")]
    refresh_token_expire_days: int = 30

    @property
    def refresh_token_expire_minutes(self):
        return 24 * 60 * self.refresh_token_expire_days


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",  # Игнорировать другие переменные в .env
    )

    rabbit_protocol: str = "amqp"
    rabbit_host: Annotated[str, Field(alias="RABBITMQ_HOST")]
    rabbit_port: Annotated[str, Field(alias="RABBITMQ_PORT")]
    rabbit_user: Annotated[str, Field(alias="RABBITMQ_USER")]
    rabbit_password: Annotated[str, Field(alias="RABBITMQ_PASSWORD")]

    @property
    def rabbitmq_url(self):
        return (
            f"{self.rabbit_protocol}://{self.rabbit_user}:{self.rabbit_password}@" \
            f"{self.rabbit_host}:{self.rabbit_port}"
        )


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )

    db_name: Annotated[str, Field(alias="POSTGRES_DB")]
    db_user: Annotated[str, Field(alias="POSTGRES_USER")]
    db_password: Annotated[str, Field(alias="POSTGRES_PASSWORD")]
    db_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    db_port: int = Field(default=6000, alias="PGPORT")
    db_echo: bool = False

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings) # type: ignore
    database: DatabaseSettings = Field(default_factory=DatabaseSettings) # type: ignore
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings) # type: ignore
    auth: AuthSettings = Field(default_factory=AuthSettings) # type: ignore

    log: LoggerSettings = LoggerSettings()


settings = Settings()
