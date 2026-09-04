# AI Health Web Assignment

흉부 X-ray 이미지로 폐렴 여부를 예측하고 환자 정보를 관리하는
FastAPI 기반 웹 서비스입니다. (오즈코딩스쿨 팀 프로젝트)

## 아키텍처

| 서비스 | 역할 |
|--------|------|
| `fastapi` | 환자 관리 / 인증 API. 예측 요청을 Redis 큐에 적재 |
| `ai-worker` | 큐에서 X-ray 추론 작업을 꺼내 PyTorch(CPU)로 폐렴 예측 후 pub/sub 으로 결과 반환. `--scale ai-worker=3` 으로 수평 확장 |
| `mysql` | 환자·예측 데이터 (SQLAlchemy + Alembic) |
| `redis` | 작업 큐 및 결과 전달 |

이미지 용량을 줄이기 위해 웹 계층(`app`)과 AI 워커(`ai`)의 의존성을 분리합니다.

## 실행

```bash
cp .env.example .env
docker compose up --build

# AI 워커 수평 확장
docker compose up -d --scale ai-worker=3
```

API 문서: http://localhost:8000/docs

## Alembic Migration Guide

이 프로젝트는 데이터베이스 마이그레이션을 위해 Alembic을 사용합니다.

### 1. 마이그레이션 파일 생성 (자동 생성)
모델(`app/models/`)이 변경된 경우 다음 명령어를 실행하여 마이그레이션 파일을 생성합니다.
```bash
uv run alembic revision --autogenerate -m "변경 내용 설명"
```

### 2. 데이터베이스에 반영
생성된 마이그레이션을 데이터베이스에 적용하려면 다음 명령어를 실행합니다.
```bash
uv run alembic upgrade head
```

### 3. 이전 상태로 되돌리기 (Rollback)
마지막 마이그레이션을 취소하려면 다음 명령어를 실행합니다.
```bash
uv run alembic downgrade -1
```
