# ── Stage 1: builder ──
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 빌드 시점에 모델 학습 -> 이미지에 굽는다 (재현 가능)
COPY train ./train
RUN MODEL_DIR=/install/models python train/train.py


# ── Stage 2: runtime ──
FROM python:3.13-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /install/models /app/models

COPY app ./app
COPY worker ./worker
COPY static ./static

RUN chown -R appuser:appuser /app
USER appuser

ENV MODEL_PATH=/app/models/risk_model.json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

# 컨테이너 자체 헬스체크도 정의해둔다 (compose 설정과 별개로 이미지 단독 실행 시 유효)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/healthcheck || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
