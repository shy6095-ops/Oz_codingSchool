from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 로컬 개발에서는 SQLite, 운영 환경에서는 MySQL 등 전체 DB URL을 직접 지정할 수 있다.
    # 설정하지 않으면 아래 MySQL 개별 설정값으로 URL을 만든다.
    DATABASE_URL: str | None = None
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

  # JWT 설정 (추가)
    SECRET_KEY: str = "change-me-in-env"
    ALGORITHM: str = "HS256"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
