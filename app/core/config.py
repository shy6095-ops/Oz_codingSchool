from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DATABASE_URL이 설정되어 있으면 SQLite 등 원하는 DB를 바로 사용할 수 있다.
    DATABASE_URL: str | None = None
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

    # 기존 JWT_SECRET_KEY 환경 변수도 함께 지원한다.
    SECRET_KEY: str = Field(
        default="change-me-in-env",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
    )
    ALGORITHM: str = "HS256"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
