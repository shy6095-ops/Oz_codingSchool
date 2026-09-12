# 챌린저 66 — Docker를 활용한 웹 서비스 배포 1일차

FastAPI 서비스를 Docker 이미지로 빌드해서 띄우고, 같은 구성을 Docker Compose 로 옮겨보는 과제.

## 1. Docker란?

컨테이너는 **애플리케이션 + 실행에 필요한 모든 것(런타임·라이브러리·설정)** 을 하나로 묶어 격리 실행하는 기술이다.

| | 가상머신(VM) | 컨테이너(Docker) |
| --- | --- | --- |
| 격리 단위 | 하드웨어 가상화 | 프로세스 격리 (호스트 커널 공유) |
| 게스트 OS | 있음 | 없음 |
| 용량 | 수 GB | 수십~수백 MB |
| 부팅 | 수십 초~분 | 1초 이내 |

핵심 개념 3가지

- **이미지(Image)** — 실행 환경을 찍어놓은 읽기 전용 템플릿. Dockerfile 로 만든다.
- **컨테이너(Container)** — 이미지를 실행한 인스턴스. 이미지 하나로 여러 개 띄울 수 있다.
- **레이어(Layer)** — Dockerfile 명령 한 줄 = 레이어 한 장. 위에서부터 바뀐 레이어만 다시 빌드된다.

> 그래서 `COPY requirements.txt` → `RUN pip install` → `COPY main.py` 순서가 중요하다.
> 소스만 고쳤을 때 `pip install` 레이어가 캐시에서 재사용돼 빌드가 몇 초로 끝난다.

## 2. Docker build & run

```bash
# 이미지 빌드 (-t : 이름:태그, . : 빌드 컨텍스트)
docker build -t challenger66-api:1.0 .

# 이미지 목록 확인
docker images

# 컨테이너 실행 (-d 백그라운드, -p 포트매핑, -e 환경변수, --name 이름)
docker run -d -p 8000:8000 -e APP_ENV=docker --name challenger66-api challenger66-api:1.0

# 동작 확인
curl http://localhost:8000/
curl -X POST http://localhost:8000/bmi \
  -H "Content-Type: application/json" \
  -d '{"height_cm":176,"weight_kg":72}'
```

### 자주 쓰는 명령어

```bash
docker ps                         # 실행 중인 컨테이너
docker ps -a                      # 종료된 것까지 전부
docker logs -f challenger66-api   # 로그 실시간 확인
docker exec -it challenger66-api bash   # 컨테이너 안으로 진입
docker stop challenger66-api      # 정지
docker rm challenger66-api        # 삭제 (정지 후에만)
docker rmi challenger66-api:1.0   # 이미지 삭제
docker system prune -a            # 안 쓰는 이미지/컨테이너 일괄 정리
```

### 포트 매핑이 왜 필요한가

컨테이너는 자기만의 네트워크 네임스페이스를 갖는다. `-p 8000:8000` 은 **호스트 8000 → 컨테이너 8000** 으로 트래픽을 흘려주는 설정이다.

그리고 uvicorn 을 반드시 `--host 0.0.0.0` 으로 띄워야 한다. 기본값 `127.0.0.1` 은 컨테이너 내부 루프백만 듣기 때문에 포트를 매핑해도 외부에서 접속이 안 된다. **1일차에 가장 많이 걸리는 함정.**

## 3. Docker Compose

`docker run` 에 붙던 긴 옵션(포트·환경변수·볼륨·재시작 정책)을 YAML 로 선언해두고 재현 가능하게 만드는 도구. 컨테이너가 2개 이상이 되는 순간부터는 사실상 필수다.

### docker-compose.yml 주요 키

| 키 | 설명 |
| --- | --- |
| `services` | 띄울 컨테이너들의 목록 |
| `build` | Dockerfile 로 직접 빌드 (`context`, `dockerfile`) |
| `image` | 빌드 결과 이미지 이름 / 또는 레지스트리에서 받아올 이미지 |
| `ports` | `"호스트:컨테이너"` 포트 매핑 |
| `environment` | 환경변수 주입 |
| `env_file` | `.env` 파일로 환경변수 일괄 주입 |
| `healthcheck` | 컨테이너 정상 여부 주기 점검 |
| `restart` | 재시작 정책 (`no` / `always` / `unless-stopped` / `on-failure`) |
| `depends_on` | 기동 순서 의존성 |
| `volumes` | 데이터 영속화 / 호스트 디렉터리 마운트 |

### 실행 및 종료

```bash
# 빌드 + 백그라운드 실행
docker compose up -d --build

# 상태 / 로그
docker compose ps
docker compose logs -f api

# 컨테이너 안에서 명령 실행
docker compose exec api bash

# 종료 (컨테이너 삭제, 볼륨은 유지)
docker compose down

# 볼륨까지 완전 삭제
docker compose down -v
```

`up -d` 와 `down` 의 차이를 기억하면 된다. `stop` 은 멈추기만 하고, `down` 은 컨테이너와 네트워크까지 정리한다.

### 컨테이너를 여러 개 띄워보기

```bash
docker compose up -d --scale api=3
```

`ports` 가 고정돼 있으면 포트 충돌이 나므로, 스케일 테스트는 `ports` 를 지우고 `docker compose exec` 로 내부에서 확인한다. `/` 응답의 `hostname` 값이 컨테이너마다 달라지는 것을 볼 수 있다.

## 파일 구성

```
66-docker-basics-build-compose/
├── main.py             # FastAPI 앱 (/, /healthcheck, POST /bmi)
├── requirements.txt
├── Dockerfile          # 줄마다 주석으로 역할 정리
├── .dockerignore       # 빌드 컨텍스트 제외 목록
├── docker-compose.yml  # 단일 서비스 + healthcheck
└── README.md
```

## 확인 포인트

- [x] `docker build` 로 이미지가 만들어진다
- [x] `docker run -p 8000:8000` 으로 API 가 응답한다
- [x] `--host 0.0.0.0` 이 없으면 접속이 안 되는 이유를 설명할 수 있다
- [x] `docker compose up -d` / `down` 으로 같은 구성을 재현할 수 있다
- [x] 환경변수를 바꿔 띄우면 `/` 응답의 `env` 값이 바뀐다
