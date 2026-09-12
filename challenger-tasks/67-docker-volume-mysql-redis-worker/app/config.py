"""환경변수 로딩. 컨테이너에서는 compose 의 environment/env_file 로 주입된다."""
import os


class Settings:
    DB_USER = os.getenv("DB_USER", "health")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "healthpw")
    # 컨테이너 네트워크에서는 호스트명이 아니라 compose 서비스명으로 접속한다.
    DB_HOST = os.getenv("DB_HOST", "mysql")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "healthcare")

    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # 예약 슬롯당 정원. 동시성 테스트에서 이 값을 넘는지 확인한다.
    SLOT_CAPACITY = int(os.getenv("SLOT_CAPACITY", "10"))

    # "none" | "redis-lock" | "db-lock"
    LOCK_STRATEGY = os.getenv("LOCK_STRATEGY", "redis-lock")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
