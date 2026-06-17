from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "МастерДеск"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/masterdesk"
    DATABASE_ECHO: bool = False

    REDIS_URL: str = "redis://redis:6379/0"

    BOT_TOKEN: str = ""

    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-haiku-4-5-20251001"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-me"
    ADMIN_EMAIL: str = "admin@masterdesk.ru"

    TRIAL_DAYS: int = 7

    SCHEDULER_TIMEZONE: str = "Europe/Moscow"

    YOOKASSA_SHOP_ID: str = "1370046"
    YOOKASSA_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
