# 챌린저 67 — Docker를 활용한 웹 서비스 배포 2일차

FastAPI · MySQL · Redis · worker **4개 컨테이너**로 진료 예약 서비스를 구성하고,
정원을 초과해서 예약이 들어가는 **동시성 문제를 재현한 뒤 해결**한다.

## 구성

| 서비스 | 이미지 | 역할 |
| --- | --- | --- |
| `api` | 직접 빌드 (`app/Dockerfile`) | 예약 API. 확정 작업을 Redis 큐에 적재 |
| `worker` | 직접 빌드 (`worker/Dockerfile`) | 큐에서 작업을 꺼내 확정 알림 처리. `--scale` 로 확장 |
| `mysql` | `mysql:8.0` | 예약 슬롯·예약 내역. 볼륨으로 영속화 |
| `redis` | `redis:7-alpine` | 작업 큐 + 분산 락. AOF 로 영속화 |

이미지 용량을 줄이기 위해 웹 계층과 워커의 의존성을 분리했다.
`api` 는 `asyncmy` 소스 빌드 때문에 `build-essential` 이 필요하지만, `worker` 는 `redis` 만 쓰므로 컴파일러 없이 빌드된다.

## 실행

```bash
cp .env.example .env
docker compose up -d --build

docker compose ps                 # 전부 healthy 확인
curl http://localhost:8000/healthcheck
```

API 문서: http://localhost:8000/docs

---

## 1. volume — 데이터를 컨테이너보다 오래 남기기

컨테이너의 파일시스템은 **컨테이너를 지우면 같이 사라진다.** DB 데이터가 여기 있으면 `docker compose down` 한 번에 전부 날아간다.

```yaml
mysql:
  volumes:
    - mysql_data:/var/lib/mysql   # 이름 있는 볼륨
volumes:
  mysql_data:
```

| 종류 | 문법 | 용도 |
| --- | --- | --- |
| 이름 있는 볼륨 | `mysql_data:/var/lib/mysql` | DB 데이터처럼 **영속화**가 필요한 것 |
| 바인드 마운트 | `./app:/app` | 개발 중 소스 즉시 반영 (`--reload`) |
| 익명 볼륨 | `/app/.venv` | 호스트가 컨테이너 경로를 **덮어쓰지 못하게 보호** |

검증:

```bash
# 예약을 몇 건 넣고
curl -X POST localhost:8000/reservations -H 'Content-Type: application/json' \
  -d '{"slot_id":1,"patient_name":"한승수"}'

docker compose down          # 컨테이너 삭제 (볼륨 유지)
docker compose up -d         # 다시 기동
curl localhost:8000/slots/1  # reserved 값이 그대로 남아있다

docker compose down -v       # 볼륨까지 삭제
docker compose up -d
curl localhost:8000/slots/1  # reserved 가 0으로 초기화
```

`down` 과 `down -v` 의 차이가 volume 의 핵심이다.

---

## 2. FastAPI 서버 & MySQL 연결

컨테이너 사이에서는 **서비스명이 호스트명**이 된다. compose 가 만든 네트워크에 DNS 를 붙여주기 때문이다.

```
DB_HOST: mysql        # localhost 가 아니다
DB_PORT: "3306"       # 호스트 매핑 포트가 아니라 컨테이너 내부 포트
```

`localhost` 를 쓰면 **컨테이너 자기 자신**을 가리켜 연결이 실패한다. 2일차에 가장 많이 걸리는 함정.

### 기동 순서 문제

`depends_on: - mysql` 만 쓰면 "MySQL 프로세스가 시작됨"까지만 기다린다. MySQL 8.0 은 초기화에 수십 초가 걸리므로, 그 사이 `api` 가 먼저 떠서 연결 실패로 죽는다.

```yaml
depends_on:
  mysql:
    condition: service_healthy   # 실제로 연결을 받는 상태까지 대기
```

여기에 더해 `app/db.py` 의 `init_db()` 에 **재시도 루프**를 뒀다. healthcheck 를 통과해도 권한 초기화가 늦는 경우가 있어서, 애플리케이션 쪽 방어가 한 겹 더 필요하다.

---

## 3. 동시성 문제 — 초과 예약

정원 10명인 슬롯에 50명이 동시에 요청하면 이런 일이 벌어진다.

```
요청 A: SELECT reserved  -> 9   (아직 여유 있음)
요청 B: SELECT reserved  -> 9   (아직 여유 있음)
요청 A: UPDATE reserved = 10
요청 B: UPDATE reserved = 10    ← A의 증가가 사라졌다 (lost update)
```

**읽기 → 확인 → 쓰기** 사이에 다른 요청이 끼어들 수 있어서, 정원을 넘겨 예약이 확정된다.

### 재현

```bash
# .env 에서 LOCK_STRATEGY=none 으로 바꾸고
docker compose up -d --force-recreate api
python load_test.py 50
```

```
 전략        : none
 정원        : 10
 요청        : 50
 성공(200)   : 27
 DB reserved : 27
 초과 예약   : 17
 ❌ 초과 예약 발생 — 동시성 제어가 필요하다.
```

### 해결 1 — Redis 분산 락 (`LOCK_STRATEGY=redis-lock`)

```python
acquired = await redis.set(key, token, nx=True, ex=ttl)
```

- `nx` — 키가 없을 때만 성공. **먼저 잡은 하나만** 통과한다
- `ex` — 만료시간. 락을 잡은 프로세스가 죽어도 자동 해제되어 **데드락을 막는다**
- `token` — 내가 건 락인지 식별. 해제는 Lua 스크립트로 원자 처리한다

`GET` 으로 확인하고 `DEL` 을 따로 하면, 그 틈에 락이 만료되고 다른 요청이 잡은 락을 풀어버릴 수 있다. 그래서 확인과 삭제가 한 번에 일어나야 한다.

### 해결 2 — DB 행 잠금 (`LOCK_STRATEGY=db-lock`)

```python
stmt = select(Slot).where(Slot.id == slot_id).with_for_update()
```

`SELECT ... FOR UPDATE` 로 트랜잭션이 끝날 때까지 해당 행을 잠근다. API 컨테이너를 여러 대로 늘려도 DB 한 곳에서 직렬화되므로 안전하다.

### 비교

| | Redis 분산 락 | DB 행 잠금 |
| --- | --- | --- |
| 잠금 위치 | Redis | MySQL |
| 범위 | 서비스 전체 (DB 밖 자원도 가능) | 해당 행 |
| 장애 시 | TTL 로 자동 해제 | 트랜잭션 종료 시 해제 |
| 비용 | 네트워크 왕복 추가 | DB 커넥션 점유 |
| 적합 | 여러 자원에 걸친 작업 | 단일 테이블 정합성 |

### 검증

```bash
# LOCK_STRATEGY=redis-lock
python load_test.py 50
```

```
 전략        : redis-lock
 정원        : 10
 요청        : 50
 성공(200)   : 10
 마감(409)   : 40
 DB reserved : 10
 초과 예약   : 0
 ✅ 정원만큼만 예약됨 — 동시성 제어 성공.
```

---

## 4. worker — 응답에서 무거운 일 떼어내기

알림 발송을 요청 안에서 처리하면 사용자가 그만큼 기다린다. 그래서 API 는 Redis 큐에 작업만 넣고 바로 응답하고, 워커가 따로 꺼내 처리한다.

```python
# api
await redis.rpush(QUEUE_KEY, json.dumps(task))

# worker
item = client.blpop(QUEUE_KEY, timeout=5)   # 큐가 빌 때까지 블로킹
```

`BLPOP` 은 큐가 빌 때까지 대기하므로 폴링이 필요 없다. 그리고 한 작업은 **워커 하나에만** 전달되므로, 컨테이너를 늘리면 그대로 분산 처리된다.

```bash
docker compose up -d --scale worker=3
docker compose logs -f worker
```

```
worker-1  | [worker a3f2…] 처리 완료: 환자001님 예약이 확정되었습니다.
worker-3  | [worker 9b81…] 처리 완료: 환자002님 예약이 확정되었습니다.
worker-2  | [worker 4c05…] 처리 완료: 환자003님 예약이 확정되었습니다.
```

처리 결과 확인:

```bash
curl localhost:8000/notifications
```

---

## 파일 구성

```
67_Docker볼륨_MySQL_Redis_워커연동/
├── app/
│   ├── main.py          # 예약 API, 3가지 락 전략 분기
│   ├── config.py        # 환경변수
│   ├── db.py            # 비동기 엔진 + MySQL 대기 재시도
│   ├── models.py        # Slot / Reservation
│   ├── redis_client.py  # 분산 락 (SET NX EX + Lua 해제)
│   └── Dockerfile       # build-essential + curl
├── worker/
│   ├── main.py          # BLPOP 루프
│   └── Dockerfile       # redis 만 (경량)
├── requirements-app.txt
├── requirements-worker.txt
├── docker-compose.yml   # 4서비스 + volume + healthcheck
├── .env.example
├── .dockerignore
├── load_test.py         # 50건 동시 요청 테스트
└── README.md
```

## 확인 포인트

- [x] 4개 컨테이너가 모두 `healthy` 로 기동
- [x] `down` / `up` 후에도 예약 데이터 유지, `down -v` 후 초기화
- [x] `DB_HOST: mysql` 로 컨테이너 간 DB 연결 (`localhost` 로는 실패하는 이유 설명 가능)
- [x] `LOCK_STRATEGY=none` 에서 초과 예약 재현
- [x] `redis-lock` / `db-lock` 에서 정원만큼만 예약
- [x] `--scale worker=3` 으로 작업이 분산 처리
