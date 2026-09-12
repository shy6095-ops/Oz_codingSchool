"""배포 환경별 설정. 값은 전부 환경변수로 주입한다 (12-Factor)."""
import os


class Settings:
    # dev | prod
    ENV = os.getenv("APP_ENV", "dev")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))
    MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/risk_model.json")

    # 쉼표로 구분된 허용 오리진. prod 에서는 반드시 좁혀야 한다.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

    # 분당 요청 제한 (IP 기준)
    RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"


settings = Settings()
