from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DATABASE_URL이 설정되면 로컬 SQLite 등 별도 데이터베이스를 사용할 수 있다.
    DATABASE_URL: str | None = None
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"
    JWT_SECRET_KEY: str = "change-this-secret-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
