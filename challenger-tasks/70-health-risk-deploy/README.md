# 챌린저 70 — Docker를 활용한 웹 서비스 배포 5일차

4일차(69)에서 만든 **당뇨 · 고혈압 위험도 예측 서비스**를 운영 가능한 형태로 배포한다.
Nginx 리버스 프록시, 환경 분리, 캐시·워커, 관측성, 요청 제한, CI 까지.

## 실행

```bash
cp .env.example .env

# 개발
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
open http://localhost:8000          # /docs 접근 가능

# 운영
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
open http://localhost               # nginx 경유, /docs 는 비활성
```

## 아키텍처

```
              ┌──────────── 80 (외부 공개) ────────────┐
[클라이언트] ─►│  nginx  압축 · 캐시 · 요청제한 · 보안헤더 │
              └───────────────────┬───────────────────┘
                                  │ 내부 네트워크 (8000 은 외부 비공개)
                     ┌────────────┴────────────┐
                     ▼                         ▼
                 api ×2                    worker ×2
              예측 · 캐시 조회            비동기 추론 처리
                     └────────────┬────────────┘
                                  ▼
                            redis  캐시 · 큐 · 요청제한 카운터
```

| 서비스 | 외부 노출 | 역할 |
| --- | --- | --- |
| `nginx` | **80** | 리버스 프록시, 정적 캐시, gzip, 보안 헤더, 요청 제한 |
| `api` | 없음 | 예측 API. 복제 2개 |
| `worker` | 없음 | 비동기 추론. 복제 2개 |
| `redis` | 없음 | 캐시 + 큐 + 요청 제한 카운터 |

---

## 1. 환경 분리 — 그리고 여기서 잡은 함정

베이스 + 오버레이 구조로 나눴다.

| 파일 | 내용 |
| --- | --- |
| `docker-compose.yml` | 공통. **호스트 포트를 열지 않는다** |
| `docker-compose.dev.yml` | api 8000 개방, `/docs` 노출, 요청 제한 느슨하게 |
| `docker-compose.prod.yml` | nginx 추가, 복제, 리소스 상한, 로그 로테이션 |

### 함정: `ports: []` 로는 포트가 닫히지 않는다

처음에는 베이스에 `ports: - "8000:8000"` 을 두고 운영 오버레이에서 `ports: []` 로 지우려 했다. 그런데 검증해 보니 포트가 **그대로 열려 있었다.**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config \
  | grep -A3 'api:' | grep published
#   published: "8000"     ← 닫히지 않았다
```

Compose 는 `ports` 를 **리스트 병합(append)** 으로 처리한다. 빈 리스트를 줘도 베이스의 매핑이 살아남는다. 운영에서 `api:8000` 이 외부에 직접 노출되면 nginx 의 요청 제한·보안 헤더를 모두 우회할 수 있어 **리버스 프록시를 둔 의미가 없어진다.**

**해결** — 베이스에서 `ports` 를 아예 빼고 `expose` 만 둔다. 포트 개방은 개발 오버레이에서만 추가한다. 덮어쓸 수 없는 값은 처음부터 넣지 않는 게 답이다.

CI 에 회귀 방지 검사를 넣어뒀다.

```yaml
- name: 운영 구성에서 api 포트가 닫혀있는지 확인
```

### prod 에서 API 문서를 닫는다

```python
docs_url = None if settings.is_prod else "/docs"
```

`/docs` 와 `/openapi.json` 은 엔드포인트·스키마·검증 규칙을 전부 드러낸다. 운영에서는 닫는다.

---

## 2. Nginx 리버스 프록시

| 설정 | 이유 |
| --- | --- |
| `upstream risk_api { server api:8000; }` | 서비스명 DNS 로 복제본에 라운드로빈 분산 |
| `keepalive 32` | 백엔드 커넥션 재사용 |
| `gzip on` | JSON·CSS·JS 응답 압축 |
| `limit_req_zone ... rate=120r/m` | 앱 레벨 제한과 **이중 방어** |
| `client_max_body_size 1m` | 과대 요청 차단 |
| `X-Forwarded-For` | 앱이 실제 클라이언트 IP 를 알아야 IP 기준 제한이 가능 |
| `X-Request-ID $request_id` | nginx 가 요청 ID 를 만들고 앱이 이어받아 로그를 연결 |
| `X-Content-Type-Options` 등 | 기본 보안 헤더 |
| `location = /nginx-health` | 백엔드를 거치지 않는 프록시 자체 헬스체크 |

`X-Forwarded-For` 를 넘기지 않으면 앱이 보는 IP 가 전부 nginx 컨테이너가 되어, 요청 제한이 **전체 사용자에게 하나로 합산**된다. 한 명이 한도를 쓰면 모두가 막힌다.

---

## 3. liveness / readiness 분리

| 엔드포인트 | 확인 대상 | 용도 |
| --- | --- | --- |
| `/healthcheck` | 프로세스만 | liveness — 죽었으면 재시작 |
| `/readyz` | 모델 + Redis | readiness — 준비 안 됐으면 트래픽 제외 |

둘을 합치면 Redis 가 잠깐 끊길 때 **정상인 앱까지 재시작**되어 장애가 번진다. 역할을 나눠야 한다. compose 의 `healthcheck` 는 `/readyz` 를 쓰고, `nginx` 는 `api` 가 `service_healthy` 가 될 때까지 기다린다.

---

## 4. 관측성 — 구조화 로깅

```python
class JsonFormatter(logging.Formatter):
    def format(self, record): return json.dumps({...})
```

로그를 JSON 한 줄로 남겨 수집기가 바로 파싱하게 한다.

```json
{"time":"2026-09-12T20:14:03","level":"INFO","message":"request",
 "request_id":"a3f21c8e9b04","method":"POST","path":"/api/predict",
 "status":200,"elapsed_ms":3.42,"client":"172.18.0.1"}
```

- `X-Request-ID` 를 nginx → api 로 이어받아 **한 요청을 양쪽 로그에서 추적**할 수 있다
- 응답에 `X-Response-Time-ms` 를 실어 클라이언트도 지연을 볼 수 있다
- `/healthcheck`, `/readyz`, `/static` 은 로그에서 제외 — 헬스체크가 10초마다 찍히면 실제 요청이 묻힌다

---

## 5. 요청 제한

```python
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 70)
```

`INCR` 은 원자적이라 **api 복제본이 여러 개여도** 카운터가 어긋나지 않는다. 프로세스 메모리에 세면 복제본마다 따로 세어 실제 한도가 `replicas` 배로 늘어난다.

분 단위 키(`int(time.time() // 60)`)를 쓰는 고정 윈도우 방식이고, TTL 70초로 분 경계에 약간 여유를 뒀다.

nginx(`120r/m`)와 앱(`60/min`) 양쪽에 둬서, nginx 가 대량 트래픽을 먼저 걷어내고 앱이 정밀하게 판단한다.

---

## 6. 캐시와 비동기 워커

| 경로 | 동작 |
| --- | --- |
| `POST /api/predict` | 캐시 조회 → 없으면 추론 후 `SETEX` 저장 (`cached` 필드로 구분) |
| `POST /api/predict/async` | 큐에 적재하고 `job_id` 반환 |
| `GET /api/predict/result/{job_id}` | 결과 조회 (`pending` / `done`) |

Redis 는 `maxmemory 256mb` + `allkeys-lru` 로 제한했다. 상한이 없으면 캐시가 계속 쌓여 컨테이너가 OOM 으로 죽는다.

### 워커의 graceful shutdown

```python
signal.signal(signal.SIGTERM, _on_signal)   # 플래그만 세운다
while not _shutdown:
    item = client.blpop(QUEUE_KEY, timeout=2)
```

`docker stop` 은 SIGTERM 을 보내고 기본 10초 뒤 SIGKILL 한다. 신호를 받자마자 죽으면 처리 중이던 작업이 사라진다. 플래그만 세우고 루프가 자연히 끝나게 해서 **진행 중 작업을 마치고** 종료한다. `blpop` 타임아웃을 2초로 짧게 둔 이유도 종료 신호에 빨리 반응하기 위해서다.

---

## 7. 운영 설정

| 항목 | 설정 | 이유 |
| --- | --- | --- |
| 로그 로테이션 | `max-size: 10m`, `max-file: 3` | 기본값은 무제한 — 디스크가 찬다 |
| 리소스 상한 | api 1 CPU/512M, worker 0.5/256M | 한 컨테이너가 호스트를 잠식하는 것을 막는다 |
| 재시작 정책 | `always` (운영) / `unless-stopped` (개발) | 운영은 호스트 재부팅 후에도 살아나야 한다 |
| 비root 실행 | `USER appuser` | 컨테이너 탈출 시 피해 축소 |
| 설정 마운트 | `:ro` | 컨테이너가 설정을 고칠 이유가 없다 |
| Redis 메모리 | `256mb` + `allkeys-lru` | OOM 방지 |

---

## 8. 테스트와 CI

`tests/test_predictor.py` — **13개 전부 통과**

```
PASS  test_두_질환_모두_예측된다
PASS  test_확률은_0과_1_사이다
PASS  test_위험군이_건강군보다_확률이_높다
PASS  test_구간_경계
PASS  test_진단기준_초과시_danger_플래그
PASS  test_건강군은_플래그가_없다
PASS  test_수정가능한_요인에만_권고한다
PASS  test_건강군에도_권고가_하나는_있다
PASS  test_기여도는_내림차순이다
PASS  test_면책조항이_포함된다
PASS  test_필수값_누락시_에러 (glucose / hba1c / systolic)

13 passed, 0 failed
```

Redis 나 네트워크 없이 도는 순수 단위 테스트라 CI 에서 빠르다.

`.github/workflows/ci.yml` 단계

1. **test** — 의존성 설치 → 모델 학습 → pytest
2. **docker** — 이미지 빌드(GHA 레이어 캐시) → 컨테이너 기동 → 예측 요청 스모크 테스트
3. **compose 검증** — dev/prod 구성 문법 확인
4. **포트 격리 검증** — 운영 구성에서 api 가 호스트에 노출되지 않는지 확인 (위 함정의 회귀 방지)

---

## 배포 확인 절차

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps    # 전부 healthy

curl -i http://localhost/nginx-health          # 프록시 자체
curl -s http://localhost/readyz                # 백엔드 준비 상태
curl -s -o /dev/null -D - http://localhost/    # 보안 헤더 · X-Request-ID 확인

# api 가 외부에 노출되지 않는지 (연결 거부되어야 정상)
curl -s --max-time 3 http://localhost:8000/ || echo "정상: 직접 접근 차단됨"

# 예측
curl -s -X POST http://localhost/api/predict -H 'Content-Type: application/json' \
  -d '{"age":52,"height_cm":176,"weight_kg":82,"systolic":138,"diastolic":88,
       "glucose":112,"hba1c":6.1,"family_history":1,"smoker":0,"exercise_days":1}'

# 캐시 동작 (두 번째는 cached:true)
# 요청 제한 (61번째부터 429)
for i in $(seq 1 70); do
  curl -s -o /dev/null -w "%{http_code} " http://localhost/api/model
done

docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api | head -20
```

---

## 파일 구성

```
70-health-risk-deploy/
├── app/
│   ├── config.py            # 환경변수 설정 (12-Factor)
│   ├── predictor.py         # 추론 + 임상 판정 + 권고
│   └── main.py              # 라우팅, 구조화 로깅, 요청 제한, liveness/readiness
├── worker/main.py           # 비동기 추론 + graceful shutdown
├── train/train.py           # 모델 학습
├── static/                  # 웹 UI
├── nginx/nginx.conf         # 리버스 프록시
├── tests/test_predictor.py  # 단위 테스트 13개
├── .github/workflows/ci.yml # 테스트 + 빌드 + 스모크 + 포트 격리 검증
├── Dockerfile               # 멀티스테이지 + 비root + HEALTHCHECK
├── docker-compose.yml       # 베이스 (포트 미개방)
├── docker-compose.dev.yml   # 개발 오버레이
├── docker-compose.prod.yml  # 운영 오버레이
├── .env.example
├── requirements.txt / requirements-dev.txt
├── .dockerignore
└── README.md
```

## 확인 포인트

- [x] nginx 를 통해서만 서비스 접근, api 포트는 외부 비공개
- [x] `ports: []` 가 동작하지 않는 함정을 찾아 구조로 해결 + CI 회귀 검사 추가
- [x] dev/prod 환경 분리, prod 에서 `/docs` 비활성화
- [x] liveness / readiness 분리
- [x] JSON 구조화 로깅 + 요청 ID 로 nginx↔api 추적
- [x] Redis 기반 요청 제한 (복제본 간 일관)
- [x] 캐시 + 비동기 워커, graceful shutdown
- [x] 로그 로테이션 · 리소스 상한 · 비root 실행
- [x] 단위 테스트 13개 통과, CI 파이프라인 구성
