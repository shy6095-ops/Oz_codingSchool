# ── Stage 1: builder — 의존성 설치 + 모델 학습 ──
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 빌드 시점에 두 모델(당뇨/고혈압)을 학습해 이미지에 굽는다.
COPY train ./train
RUN MODEL_DIR=/install/models python train/train.py


# ── Stage 2: runtime — 실행에 필요한 것만 ──
FROM python:3.13-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /install/models /app/models

COPY app ./app
COPY static ./static

RUN chown -R appuser:appuser /app
USER appuser

ENV MODEL_PATH=/app/models/risk_model.json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
