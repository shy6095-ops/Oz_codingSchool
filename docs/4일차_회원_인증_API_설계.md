# 4일차 회원 · 인증 API 설계

## 1. 개요

[사용자 요구사항 정의서](요구사항_정의서.md)의 `REQ-USER-001~009`, `NFR-USER-001` 을 기반으로 설계한 회원 가입 · 인증 · 회원 관리 API 명세다.

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1/users` |
| 인증 방식 | JWT Bearer (`Authorization: Bearer <access_token>`) |
| 리프레시 토큰 | `httponly` 쿠키 (`refresh_token`), 본문에 노출하지 않음 |
| 저장소 | MySQL `users` 테이블 |
| 비밀번호 저장 | bcrypt 해시 (평문 저장·응답 금지) |

### 1.1 열거형 값

| 필드 | 값 | 설명 |
| --- | --- | --- |
| `role` | `PENDING` / `STAFF` / `ADMIN` | 가입 직후에는 항상 `PENDING`. 변경은 관리자만 가능 |
| `department` | `MEDICAL` / `DEV` / `RESEARCH` | 환자·진료기록 **등록**은 `MEDICAL` 만 가능 |
| `gender` | `M` / `F` | |

### 1.2 토큰 정책 — NFR-USER-001

| 항목 | 값 |
| --- | --- |
| 액세스 토큰 만료 | 30분 |
| 리프레시 토큰 만료 | 7일 |
| 서명 알고리즘 | HS256 (`SECRET_KEY` 는 `.env` 로 주입) |
| 페이로드 | `sub`(user_id) · `type`(`access`/`refresh`) · `iat` · `exp` — 그 외 개인정보 미포함 |
| 리프레시 쿠키 속성 | `httponly=true`, `secure=true`, `samesite=lax`, `path=/api/v1/users/token`, `max-age=7일` |

- `type` 클레임을 검증하므로 액세스 토큰으로 재발급을 시도하거나, 리프레시 토큰으로 API 를 호출하면 `401` 이다.
- 쿠키 `path` 를 `/api/v1/users/token` 으로 제한하여 일반 API 요청에는 리프레시 토큰이 실려가지 않는다.

### 1.3 공통 에러

| 상태 코드 | 의미 |
| --- | --- |
| 400 | 요청은 유효하나 처리 조건 불충족 (수정 항목 없음, 기존 비밀번호 불일치) |
| 401 | 미인증 / 토큰 없음 · 만료 · 위조 / 로그인 실패 |
| 403 | 권한 부족 (관리자 아님, 비활성 계정) |
| 404 | 대상 회원 없음 |
| 409 | 이메일 · 휴대폰번호 중복 |
| 422 | 입력값 형식 오류 (FastAPI 기본 검증 형식) |

오류 응답 형식은 다른 도메인과 동일하다.

```json
{ "detail": "이미 사용 중인 이메일입니다." }
```

---

## 2. 인증 API

### 2.1 회원가입 — REQ-USER-001

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/users/signup` |
| 인증 | 불필요 |
| 성공 | `201 Created` |

요청 본문:

```json
{
  "email": "doctor@hospital.com",
  "password": "password1234",
  "name": "김의사",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678"
}
```

| 필드 | 제약 |
| --- | --- |
| `email` | 이메일 형식, 유일 |
| `password` | 8~64자 |
| `name` | 1~20자 |
| `department` | `MEDICAL` / `DEV` / `RESEARCH` |
| `gender` | `M` / `F` |
| `phone_number` | `01[016789]-?xxx(x)-?xxxx`, 최대 20자, 유일 |

성공 응답 (`UserResponse`):

```json
{
  "id": 1,
  "email": "doctor@hospital.com",
  "name": "김의사",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-09-07T10:00:00"
}
```

- 가입 시 역할은 **항상 `PENDING`** 으로 설정된다. 요청 본문에 `role` 을 넣어도 무시된다.
- 실패: `409` 이메일 중복 / `409` 휴대폰번호 중복 / `422` 형식 오류

### 2.2 로그인 — REQ-USER-002

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/users/login` |
| 인증 | 불필요 |
| 성공 | `200 OK` |

```json
{ "email": "doctor@hospital.com", "password": "password1234" }
```

성공 응답 본문 + `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/users/token`

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

- 실패: `401` 이메일 또는 비밀번호 불일치 — **어느 쪽이 틀렸는지 구분하지 않는다** (계정 존재 여부 노출 방지) / `403` 비활성 계정

### 2.3 액세스 토큰 재발급 — NFR-USER-001

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/users/token/refresh` |
| 인증 | `refresh_token` 쿠키 (Authorization 헤더 아님) |
| 성공 | `200 OK` |

응답은 로그인과 동일한 `TokenResponse` 이며, 새 액세스 토큰만 발급한다 (리프레시 토큰 회전 없음).

- 실패: `401` 쿠키 없음 / 만료 / 위조 / 토큰 타입 불일치 / 탈퇴·비활성 사용자

### 2.4 로그아웃 — REQ-USER-003

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/users/logout` |
| 인증 | 필요 |
| 성공 | `200 OK` |

```json
{ "message": "로그아웃 되었습니다." }
```

- 서버가 `refresh_token` 쿠키를 삭제한다. 액세스 토큰은 만료(30분) 전까지 유효하므로 클라이언트가 저장소에서 폐기해야 한다. → 서버 측 토큰 블랙리스트는 범위 밖 (필요 시 확장 과제)

---

## 3. 마이페이지 API

### 3.1 내 정보 조회 — REQ-USER-006

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/users/me` |
| 인증 | 필요 |
| 성공 | `200 OK`, 응답은 `UserResponse` (2.1과 동일) |

### 3.2 내 정보 수정 — REQ-USER-007

| 항목 | 내용 |
| --- | --- |
| Endpoint | `PATCH /api/v1/users/me` |
| 인증 | 필요 |
| 성공 | `200 OK`, 응답은 `UserResponse` |

```json
{ "department": "RESEARCH", "phone_number": "010-9876-5432" }
```

- 수정 가능한 필드는 `department`, `phone_number` **둘뿐**이다. 이메일·이름·역할은 본인이 바꿀 수 없다.
- 실패: `400` 수정할 항목 없음 / `409` 다른 회원이 쓰는 휴대폰번호 / `422` 형식 오류

### 3.3 비밀번호 변경 — REQ-USER-008

| 항목 | 내용 |
| --- | --- |
| Endpoint | `PATCH /api/v1/users/me/password` |
| 인증 | 필요 |
| 성공 | `200 OK` — `{"message": "비밀번호가 변경되었습니다."}` |

```json
{ "current_password": "password1234", "new_password": "newpassword5678" }
```

- 실패: `400` 기존 비밀번호 불일치 / `422` 새 비밀번호 길이(8~64자) 위반

### 3.4 회원 탈퇴 — REQ-USER-009

| 항목 | 내용 |
| --- | --- |
| Endpoint | `DELETE /api/v1/users/me` |
| 인증 | 필요 |
| 성공 | `200 OK` — `{"message": "회원 탈퇴가 완료되었습니다."}` |

- 회원 레코드를 삭제하고 `refresh_token` 쿠키를 제거한다. (하드 삭제 — 요구사항 정의서 OPEN-04 참고)

---

## 4. 관리자 API

### 4.1 회원 목록 조회 — REQ-USER-004

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/users` |
| 인증 | 필요 + `role = ADMIN` |
| 성공 | `200 OK` |

쿼리 파라미터:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `search` | string | — | 이메일 또는 이름 부분 검색 |
| `department` | `MEDICAL`/`DEV`/`RESEARCH` | — | 부서 필터 |
| `offset` | integer (≥0) | `0` | 건너뛸 개수 |
| `limit` | integer (1~100) | `20` | 조회 개수 |

```json
{
  "total": 42,
  "items": [
    {
      "id": 1,
      "email": "doctor@hospital.com",
      "name": "김의사",
      "department": "MEDICAL",
      "gender": "M",
      "phone_number": "010-1234-5678",
      "role": "STAFF",
      "is_active": true,
      "created_at": "2026-09-07T10:00:00"
    }
  ]
}
```

> 환자 API 는 `page`/`size` 방식, 회원 목록은 `offset`/`limit` 방식으로 페이지네이션 규약이 다르다. 현재 프론트엔드가 이 형태로 구현되어 있어 그대로 유지하되, 향후 통일 여부는 팀 논의 대상이다.

- 실패: `401` 미인증 / `403` 관리자 아님

### 4.2 회원 권한 변경 — REQ-USER-005

| 항목 | 내용 |
| --- | --- |
| Endpoint | `PATCH /api/v1/users/{user_id}/role` |
| 인증 | 필요 + `role = ADMIN` |
| 성공 | `200 OK`, 응답은 변경된 회원의 `UserResponse` |

```json
{ "role": "STAFF" }
```

- 가입 대기(`PENDING`) 회원을 승인하는 용도로 사용한다.
- 실패: `403` 관리자 아님 / `404` 대상 회원 없음 / `422` 허용되지 않는 역할 값

---

## 5. 권한 매트릭스

| 엔드포인트 | 비로그인 | PENDING/STAFF | ADMIN | MEDICAL 부서 |
| --- | --- | --- | --- | --- |
| `POST /users/signup`, `POST /users/login` | ✅ | ✅ | ✅ | ✅ |
| `POST /users/token/refresh` | 쿠키 보유 시 ✅ | ✅ | ✅ | ✅ |
| `POST /users/logout`, `/users/me` 계열 | ❌ 401 | ✅ | ✅ | ✅ |
| `GET /users`, `PATCH /users/{id}/role` | ❌ 401 | ❌ 403 | ✅ | 부서 무관 |
| `POST /patients`, `POST /patients/{id}/medical-records` | ❌ 401 | ❌ 403 | 부서에 따름 | ✅ |
| 환자·진료기록·예측 조회 | ❌ 401 | ✅ | ✅ | ✅ |

> 등록 권한은 **역할이 아니라 부서(`MEDICAL`)** 로 통제한다. 관리자라도 부서가 `MEDICAL` 이 아니면 환자를 등록할 수 없다.

---

## 6. 비고

- 프론트엔드는 액세스 토큰을 메모리/스토리지에 보관하고, `401` 응답을 받으면 `POST /users/token/refresh` 로 재발급을 시도한 뒤 원 요청을 재시도한다. (`static/apis.js`)
- `secure=true` 쿠키이므로 **HTTPS 환경에서만 리프레시 토큰이 전달된다.** 최신 브라우저는 `http://localhost` 를 신뢰 출처로 예외 취급하므로 로컬 개발에는 문제가 없지만, **HTTP 로 노출되는 서버 IP/도메인에 배포하면 리프레시가 동작하지 않는다.** 따라서 AWS 배포 시 HTTPS 구성이 전제된다. (배포 문서에서 다룸)
