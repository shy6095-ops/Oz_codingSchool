# syntax=docker/dockerfile:1

# 폐렴 예측 AI 워커 이미지 (Stage 3 3-2).
# 빌드 컨텍스트는 프로젝트 루트(docker-compose.yml의 build.context: .)를 기준으로 한다.
# fastapi 앱 이미지와 분리되어 있고, ai 의존성(torch-cpu / torchvision / pillow / redis)만 설치한다.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

# 의존성 파일만 먼저 복사해 레이어 캐시를 살린다.
# ai extra 만 설치 (fastapi / sqlalchemy / alembic 등 웹 의존성 제외)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --extra ai

# 워커 소스 + 학습된 가중치(worker/models/*.pth)
COPY worker ./worker

# Redis 연결 가능 여부로 헬스체크
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import os,redis; redis.Redis.from_url(os.environ.get('REDIS_URL','redis://localhost:6379/0')).ping()" || exit 1

CMD ["python", "-m", "worker.main"]
