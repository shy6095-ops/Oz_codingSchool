from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

    # JWT 설정 (추가)
    SECRET_KEY: str = "change-me-in-env"
    ALGORITHM: str = "HS256"

    # Redis (Stage 3: AI 워커 분리)
    # 로컬 uv 실행은 localhost, docker-compose 에서는 서비스명(redis)으로 덮어씀
    REDIS_URL: str = "redis://localhost:6379/0"

    # 폐렴 예측에 사용하는 모델 이름.
    # worker/model.py 의 MODEL_NAME 과 반드시 일치해야 한다
    # (FastAPI 는 이 값으로 (record_id, ai_model) 캐시 조회를 하고,
    #  실제 저장되는 값은 워커가 결과에 담아 보낸 ai_model 을 사용한다).
    AI_MODEL_NAME: str = "resnet18-pneumonia-v1"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
