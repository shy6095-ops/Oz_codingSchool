# syntax=docker/dockerfile:1

# FastAPI 앱 이미지를 빌드하기 위한 Dockerfile입니다.
# 빌드 컨텍스트는 프로젝트 루트(docker-compose.yml의 build.context: .)를 기준으로 합니다.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# uv 바이너리 설치 (공식 uv 이미지에서 복사)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# asyncmy 등 일부 의존성은 플랫폼용 사전빌드 wheel이 없어 소스 빌드가 필요함 (gcc 필요)
# curl은 docker-compose.yml의 healthcheck(curl -f ...)에서 사용
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일만 먼저 복사하여 소스 코드 변경 시에도 의존성 레이어가 캐시되도록 함
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 애플리케이션 소스 복사 (worker/: prediction_service.py가 import하는 AI 모델 코드/가중치)
COPY app ./app
COPY worker ./worker

RUN uv sync --frozen --no-dev

EXPOSE 8000

# 참고: Server Workers - Uvicorn with Workers (FastAPI docs)
# 로컬 개발환경(docker-compose.yml)에서는 entrypoint로 --reload 옵션을 덮어써서 실행합니다.
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
