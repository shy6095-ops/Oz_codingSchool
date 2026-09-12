# 챌린저 68 — Docker를 활용한 웹 서비스 배포 3일차

Docker 전반을 정리하고, **FastAPI + Redis 로 모델을 서빙**한다.
멀티스테이지 빌드로 이미지를 최적화하는 것이 이번 과제의 핵심.

## 구성

| 서비스 | 역할 |
| --- | --- |
| `api` | 동기 추론(+Redis 캐시), 비동기 추론 작업 적재 |
| `worker` | 큐에서 작업을 꺼내 추론하고 결과를 Redis 에 저장 |
| `redis` | 결과 캐시 + 작업 큐 |

`api` 와 `worker` 는 **같은 이미지**를 쓰고 실행 명령만 다르게 준다. 빌드가 한 번만 돌고 두 컨테이너의 모델 버전이 어긋날 일이 없다.

## 실행

```bash
docker compose up -d --build
curl http://localhost:8000/healthcheck
```

API 문서: http://localhost:8000/docs

---

## 1. Docker 전반 정리

### 이미지 · 레이어 · 캐시

Dockerfile 명령 한 줄이 레이어 한 장이다. 빌드할 때 **바뀐 레이어와 그 아래 전부**가 다시 만들어진다. 그래서 **자주 바뀌는 것을 뒤에** 둬야 한다.

```dockerfile
COPY requirements.txt .          # 거의 안 바뀜
RUN pip install -r requirements.txt   # ← 캐시 유지
COPY app ./app                   # 자주 바뀜
```

순서를 뒤집으면 코드 한 줄만 고쳐도 `pip install` 이 매번 다시 돈다. `Dockerfile.naive` 가 그 잘못된 예다.

### 주요 명령 한눈에

| 목적 | 명령 |
| --- | --- |
| 이미지 빌드 | `docker build -t name:tag .` |
| 실행 | `docker run -d -p 8000:8000 name:tag` |
| 실행 중 목록 | `docker ps` / 전체 `docker ps -a` |
| 로그 | `docker logs -f <컨테이너>` |
| 내부 진입 | `docker exec -it <컨테이너> bash` |
| 레이어 이력 | `docker history name:tag` |
| 용량 확인 | `docker images` / `docker system df` |
| 정리 | `docker system prune -a` |

### 네트워크

compose 는 프로젝트마다 브리지 네트워크를 만들고 **서비스명에 DNS** 를 붙인다. 그래서 `redis://redis:6379` 처럼 서비스명으로 접속한다. `localhost` 는 컨테이너 자기 자신이다.

| 종류 | 설명 |
| --- | --- |
| `bridge` | 기본값. 컨테이너끼리 격리된 사설망 |
| `host` | 호스트 네트워크 공유 (Linux 전용, 포트 매핑 불필요) |
| `none` | 네트워크 없음 |

### 볼륨

| 종류 | 용도 |
| --- | --- |
| 이름 있는 볼륨 | DB·Redis 데이터 영속화 |
| 바인드 마운트 | 개발 중 소스 즉시 반영 |
| 익명 볼륨 | 호스트가 컨테이너 경로를 덮어쓰지 못하게 보호 |

`docker compose down` 은 볼륨을 남기고, `down -v` 는 지운다.

---

## 2. 이미지 최적화 — 멀티스테이지 빌드

**문제**: 학습 도구·컴파일러·pip 캐시가 최종 이미지에 남으면 용량이 불고 공격면도 넓어진다.

**해결**: 빌드 단계와 실행 단계를 나누고, 실행에 필요한 것만 복사한다.

```dockerfile
FROM python:3.13-slim AS builder
RUN pip install --prefix=/install -r requirements.txt
RUN MODEL_PATH=/install/model.json python train/train.py   # 빌드 시점에 학습

FROM python:3.13-slim AS runtime
COPY --from=builder /install /usr/local                    # 패키지만
COPY --from=builder /install/model.json /app/model/model.json   # 모델만
```

`builder` 스테이지는 최종 이미지에 **포함되지 않는다.** 학습 스크립트도, 빌드 캐시도 남지 않는다.

### 비교해보기

```bash
docker build -f Dockerfile.naive -t serving:naive .
docker build -f Dockerfile       -t serving:multi .
docker images | grep serving
```

`Dockerfile.naive` 가 일부러 틀려놓은 4가지

1. 소스를 먼저 `COPY` → 코드 한 줄 수정에 `pip install` 재실행
2. `build-essential` 이 최종 이미지에 잔류
3. `--no-cache-dir` 누락 → pip 캐시 잔류
4. `root` 로 실행

### 적용한 최적화

| 항목 | 방법 |
| --- | --- |
| 베이스 이미지 | `python:3.13-slim` (full 대비 훨씬 작음) |
| 빌드 도구 분리 | 멀티스테이지 (`builder` → `runtime`) |
| pip 캐시 제거 | `--no-cache-dir` |
| apt 캐시 제거 | `rm -rf /var/lib/apt/lists/*` 를 같은 `RUN` 안에서 |
| 레이어 캐시 활용 | 의존성 → 소스 순서 |
| 빌드 컨텍스트 축소 | `.dockerignore` |
| 권한 축소 | `useradd` + `USER appuser` (비root 실행) |
| `.pyc` 미생성 | `PYTHONDONTWRITEBYTECODE=1` |

> `apt-get install` 과 `rm -rf /var/lib/apt/lists/*` 를 **별도 `RUN` 으로 나누면 의미가 없다.**
> 삭제가 새 레이어에서 일어나 아래 레이어의 캐시는 그대로 남는다. 반드시 같은 `RUN` 안에서 지워야 한다.

---

## 3. 모델 서빙

### 모델과 서빙의 분리

`train/train.py` 가 표준 라이브러리만으로 로지스틱 회귀를 학습하고, **계수만 JSON 으로** 남긴다. 서빙 컨테이너는 그 JSON 을 읽어 추론하므로 무거운 ML 런타임이 필요 없다.

```
학습 (train/train.py)  ──►  model/model.json  ──►  추론 (app/model.py)
```

학습 결과 — 데이터 생성에 쓴 "진짜" 계수를 잘 복원했다.

| 항목 | 실제 계수 | 학습된 계수 |
| --- | --- | --- |
| glucose | 1.3 | 1.332 |
| bmi | 0.9 | 0.859 |
| systolic | 0.8 | 0.717 |
| smoker | 0.6 | 0.631 |
| age | 0.5 | 0.531 |

테스트셋 성능: **accuracy 0.783 · precision 0.681 · recall 0.621 · F1 0.650**

### 추론 검증

```
bmi=21.0  sbp=112  glu=88   age=30  비흡연  ->  0.017  낮음
bmi=24.0  sbp=125  glu=100  age=45  비흡연  ->  0.189  낮음
bmi=31.5  sbp=152  glu=141  age=58  흡연    ->  0.998  매우 높음
```

### 모델 로딩은 기동 시 한 번만

```python
@lru_cache(maxsize=1)
def load_model() -> dict: ...
```

`lifespan` 에서 미리 호출해 **첫 요청이 느려지는 cold start** 를 없앤다. 요청마다 파일을 읽으면 디스크 I/O 가 응답 시간에 그대로 더해진다.

### 표준화 기준을 함께 저장하는 이유

학습 때 쓴 평균·표준편차를 `model.json` 의 `norm` 에 넣어두고 추론에서도 같은 값을 쓴다. 이 기준이 어긋나면 모델은 정상인데 결과가 망가진다 (**training-serving skew**).

---

## 4. Redis — 캐시와 큐

### 동기 추론 + 캐시

```
POST /predict
```

입력을 **정렬 직렬화 후 해시**해서 캐시 키로 쓴다. JSON 키 순서가 달라도 같은 캐시에 맞는다.

```bash
curl -X POST localhost:8000/predict -H 'Content-Type: application/json' \
  -d '{"bmi":31.5,"systolic":152,"glucose":141,"age":58,"smoker":1}'
# {"probability":0.998,"risk":"매우 높음", ... ,"cached":false}

# 같은 요청 재실행
# {"probability":0.998, ... ,"cached":true}    ← 추론 생략

curl localhost:8000/cache/stats
```

TTL(`CACHE_TTL=300`)을 둬서 모델을 교체했을 때 오래된 결과가 무한히 남지 않게 한다.

### 비동기 추론 (큐 + 워커)

모델이 무거워지면 요청 안에서 추론할 수 없다. 큐에 넣고 job_id 를 먼저 돌려준다.

```bash
JOB=$(curl -s -X POST localhost:8000/predict/async -H 'Content-Type: application/json' \
  -d '{"bmi":31.5,"systolic":152,"glucose":141,"age":58,"smoker":1}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')

curl localhost:8000/predict/result/$JOB
```

워커 확장:

```bash
docker compose up -d --scale worker=3
docker compose logs -f worker
```

`BLPOP` 은 큐가 빌 때까지 블로킹하므로 폴링이 없고, 한 작업은 워커 하나에만 전달되어 자연히 분산된다.

### 설명 가능성

응답의 `contributions` 는 각 항목이 위험도에 기여한 크기를 절댓값 순으로 보여준다. "왜 위험하다고 판단했는지"를 사용자에게 설명할 수 있다.

---

## 파일 구성

```
68-docker-multistage-model-serving/
├── train/train.py       # 표준 라이브러리 로지스틱 회귀 학습
├── model/model.json     # 학습 산출물 (계수 + 표준화 기준 + 성능)
├── app/
│   ├── model.py         # 계수 로드 + 추론 (lru_cache)
│   └── main.py          # /predict, /predict/async, /model, /cache/stats
├── worker/main.py       # BLPOP 추론 워커
├── Dockerfile           # 멀티스테이지 (builder → runtime, 비root)
├── Dockerfile.naive     # 비교용 안티패턴
├── docker-compose.yml   # api + worker(이미지 공유) + redis
├── requirements.txt
├── .dockerignore
└── README.md
```

## 확인 포인트

- [x] 레이어 캐시가 왜 순서에 의존하는지 설명할 수 있다
- [x] 멀티스테이지로 빌드 도구를 최종 이미지에서 제거했다
- [x] 비root 사용자로 실행한다
- [x] `Dockerfile.naive` 와 이미지 용량을 비교했다
- [x] 모델을 기동 시 1회만 로드한다 (cold start 제거)
- [x] 같은 입력이 캐시로 즉시 응답된다
- [x] 비동기 추론이 워커로 분산 처리된다
