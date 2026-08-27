import secrets

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./db/ai_health.db"

    ACCESS_TOKEN_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    REFRESH_TOKEN_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 30
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7
    SECURE_COOKIES: bool = True

    BOOTSTRAP_ADMIN_EMAIL: str | None = None
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None
    BOOTSTRAP_ADMIN_NAME: str | None = None
    BOOTSTRAP_ADMIN_PHONE_NUMBER: str | None = None
    BOOTSTRAP_ADMIN_DEPARTMENT: str | None = None
    BOOTSTRAP_ADMIN_GENDER: str | None = None

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def bootstrap_admin_is_configured(self) -> bool:
        return all(
            (
                self.BOOTSTRAP_ADMIN_EMAIL,
                self.BOOTSTRAP_ADMIN_PASSWORD,
                self.BOOTSTRAP_ADMIN_NAME,
                self.BOOTSTRAP_ADMIN_PHONE_NUMBER,
                self.BOOTSTRAP_ADMIN_DEPARTMENT,
                self.BOOTSTRAP_ADMIN_GENDER,
            )
        )


settings = Settings()
