from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

    # JWT / 쿠키 설정
    SECRET_KEY: str = "change-me-in-env"
    ALGORITHM: str = "HS256"
    SECURE_COOKIES: bool = True

    # 로컬 통합 테스트용 계정 bootstrap. 명시적으로 활성화한 경우에만 실행한다.
    BOOTSTRAP_TEST_USER_ENABLED: bool = False
    BOOTSTRAP_TEST_USER_EMAIL: str = ""
    BOOTSTRAP_TEST_USER_PASSWORD: str = ""
    BOOTSTRAP_TEST_USER_NAME: str = "테스트 사용자"
    BOOTSTRAP_TEST_USER_PHONE_NUMBER: str = "01000000000"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
