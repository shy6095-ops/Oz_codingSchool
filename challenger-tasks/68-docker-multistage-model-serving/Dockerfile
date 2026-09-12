# ============================================================
# 멀티스테이지 빌드
#   builder : 의존성 설치 + 모델 학습 (빌드 도구가 필요한 단계)
#   runtime : 실행에 필요한 것만 복사 (최종 이미지에 남는 단계)
# 최종 이미지에 컴파일러/학습 스크립트/캐시가 남지 않아 용량과 공격면이 줄어든다.
# ============================================================

# ── Stage 1: builder ──
FROM python:3.13-slim AS builder

WORKDIR /build

# --prefix 로 한 곳에 모아 설치해두면 다음 스테이지로 통째로 복사하기 쉽다.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 빌드 시점에 모델을 학습해 이미지에 굽는다.
# 표준 라이브러리만 쓰므로 학습에도 추가 의존성이 필요 없다.
COPY train ./train
RUN MODEL_PATH=/install/model.json python train/train.py


# ── Stage 2: runtime ──
FROM python:3.13-slim AS runtime

# curl 은 healthcheck 용. 빌드 도구(gcc 등)는 넣지 않는다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# root 로 돌리지 않는다. 컨테이너가 뚫려도 권한이 제한된다.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# builder 에서 설치한 패키지와 학습된 모델만 가져온다.
COPY --from=builder /install /usr/local
COPY --from=builder /install/model.json /app/model/model.json

COPY app ./app
COPY worker ./worker

RUN chown -R appuser:appuser /app
USER appuser

ENV MODEL_PATH=/app/model/model.json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
