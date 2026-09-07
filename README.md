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

## 문서

| 문서 | 내용 |
| --- | --- |
| [요구사항 정의서](docs/요구사항_정의서.md) | 전 도메인 기능/비기능 요구사항 ID 체계, 인수 조건, 추적 매트릭스 |
| [1일차 팀 규칙](docs/1일차_team_rules.md) | 코어타임·커밋/리뷰 규칙 |
| [2일차 Git 브랜치 전략](docs/2일차_git_branch_전략.md) | Git Flow / GitHub Flow |
| [3일차 프로젝트 뜯어보기](docs/3일차_프로젝트_뜯어보기.md) · [DB 마이그레이션](docs/3일차_db_migration.md) | 초기 구조 분석, Alembic |
| [4일차 회원·인증 API 설계](docs/4일차_회원_인증_API_설계.md) | 가입/로그인/토큰/마이페이지/관리자 API |
| [5일차 환자 관리 API 설계](docs/5일차_환자관리_API_설계.md) | 환자·진료기록 API |
| [6일차 폐렴 예측 API 설계](docs/6일차_폐렴예측_API_설계.md) | AI 예측 API |
| [7일차 앱 실행 화면](docs/7일차_앱_실행화면.md) | 프론트엔드 화면 캡처 |
| [8일차 Docker 컨테이너화](docs/8일차_Docker_컨테이너화.md) | compose 구성과 트러블슈팅 |
| [9일차 아키텍처 설계](docs/9일차_동시성문제_해결을위한_아키텍처설계.md) | 동시성 문제와 Event-Driven Architecture |

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
