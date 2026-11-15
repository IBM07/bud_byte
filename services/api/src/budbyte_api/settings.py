"""Typed runtime configuration. Everything comes from environment variables (12-factor)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BUDBYTE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Environment = "development"
    log_level: str = "INFO"
    service_name: str = "budbyte-api"

    database_url: SecretStr | None = None
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    run_migrations_on_startup: bool = True

    telegram_bot_token: SecretStr | None = None
    telegram_webhook_secret: SecretStr | None = None
    telegram_path_secret: SecretStr | None = None

    sentry_dsn: SecretStr | None = None
    web_origin: str = "http://localhost:3000"

    @field_validator(
        "database_url",
        "redis_url",
        "telegram_bot_token",
        "telegram_webhook_secret",
        "telegram_path_secret",
        "sentry_dsn",
        mode="before",
    )
    @classmethod
    def _blank_means_unset(cls, value: Any, info: ValidationInfo) -> Any:
        """A blank `KEY=` line in .env means "not set", not "set to an empty string"."""
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str) and not raw.strip():
            return cls.model_fields[info.field_name or ""].default
        return value

    @model_validator(mode="after")
    def _require_secrets_outside_dev(self) -> Self:
        if self.environment in ("staging", "production"):
            missing = [
                name
                for name in (
                    "database_url",
                    "telegram_bot_token",
                    "telegram_webhook_secret",
                    "telegram_path_secret",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"missing required settings for {self.environment}: {missing}")
        return self

    @property
    def is_prod_like(self) -> bool:
        return self.environment in ("staging", "production")


def secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value is not None else None
