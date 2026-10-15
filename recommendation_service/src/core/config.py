import logging

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggerSettings(BaseModel):
    level: int = logging.INFO
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    log_format: str = (
        "[%(asctime)s] %(levelname)s - %(message)s"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051

    log: LoggerSettings = Field(
        default_factory=LoggerSettings
    )


settings = Settings()