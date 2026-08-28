# 4일차 - User API 설계

## 1. 개요
`4일차 - User 사용자 요구사항 정의서`(`REQ-USER-001~009`, `NFR-USER-001~003`)를 기반으로 설계한 User 도메인 API 명세서입니다. 데이터 모델은 `app/models/user.py`에 정의된 `User`(이메일/비밀번호/이름/부서/성별/전화번호/권한) 스키마를 따릅니다.

- Base URL: `/api/v1`
- 인증 방식: JWT (Access Token, Refresh Token)
- 응답 포맷: `application/json`
- 공통 헤더: 인증이 필요한 API는 `Authorization: Bearer <access_token>` 필요

### 공통 Enum 값
| 항목 | 값 | 비고 |
|---|---|---|
| gender | `M`, `F` | |
| department | `MEDICAL`, `DEV`, `RESEARCH` | 의료 / 개발 / 연구 |
| role | `PENDING`, `STAFF`, `ADMIN` | 대기자 / 스태프 / 어드민 |

### 공통 에러 응답
```json
{
  "detail": "에러 메시지"
}
```
| 상태 코드 | 의미 |
|---|---|
| 400 | 요청 값 검증 실패 |
| 401 | 인증 실패 (토큰 없음/만료) |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 중복(이메일/전화번호 등) |

---

## 2. 엔드포인트 명세

### 2.1 회원가입
- **요구사항 ID**: REQ-USER-001
- **Method / Path**: `POST /api/v1/users`
- **인증**: 불필요
- **설명**: 사내 의료진/개발 실무진이 회원가입을 진행합니다. 가입 직후 권한은 기본값 `PENDING`(대기자)이며, 관리자가 승인(REQ-USER-005) 전까지 서비스를 이용할 수 없습니다.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "010-1234-5678"
}
```

**Response `201 Created`**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-08-27T10:00:00"
}
```

**에러**
- `409` 이메일/전화번호 중복

---

### 2.2 로그인
- **요구사항 ID**: REQ-USER-002, NFR-USER-001
- **Method / Path**: `POST /api/v1/auth/login`
- **인증**: 불필요
- **설명**: 이메일/비밀번호 검증 후 JWT를 발급합니다. Access Token은 응답 바디로, Refresh Token은 `HttpOnly` 쿠키로 전달합니다. JWT payload에는 최소 식별 정보인 `user_id`만 포함합니다.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response `200 OK`**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```
- `Set-Cookie: refresh_token=<token>; HttpOnly; Path=/api/v1/auth; Max-Age=604800`

**에러**
- `401` 이메일/비밀번호 불일치

---

### 2.3 Access Token 재발급
- **요구사항 ID**: NFR-USER-001
- **Method / Path**: `POST /api/v1/auth/refresh`
- **인증**: Refresh Token 쿠키 필요
- **설명**: Access Token 만료 시, 쿠키의 Refresh Token으로 재발급합니다. Refresh Token도 만료된 경우 `401`을 반환해 재로그인을 유도합니다.

**Response `200 OK`**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**에러**
- `401` Refresh Token 없음/만료

---

### 2.4 로그아웃
- **요구사항 ID**: REQ-USER-003
- **Method / Path**: `POST /api/v1/auth/logout`
- **인증**: 필요
- **설명**: 서버에서 Refresh Token을 무효화하고, 클라이언트 쿠키를 삭제합니다.

**Response `204 No Content`**
- `Set-Cookie: refresh_token=; HttpOnly; Path=/api/v1/auth; Max-Age=0`

---

### 2.5 회원 목록 조회 (Admin)
- **요구사항 ID**: REQ-USER-004
- **Method / Path**: `GET /api/v1/users`
- **인증**: 필요 (`role=ADMIN`)
- **설명**: 관리자가 전체 회원 목록을 조회합니다. 이메일/이름 검색 및 부서 필터를 지원합니다.

**Query Parameters**
| 이름 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `search` | string | N | 이메일 또는 이름 부분 일치 검색 |
| `department` | string | N | `MEDICAL` / `DEV` / `RESEARCH` |
| `page` | int | N | 기본값 1 |
| `size` | int | N | 기본값 20 |

**Response `200 OK`**
```json
{
  "total": 42,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": 1,
      "email": "user@example.com",
      "name": "홍길동",
      "department": "DEV",
      "gender": "M",
      "phone_number": "010-1234-5678",
      "is_active": true
    }
  ]
}
```

**에러**
- `403` ADMIN이 아닌 사용자가 호출

---

### 2.6 회원 권한 변경 (Admin)
- **요구사항 ID**: REQ-USER-005
- **Method / Path**: `PATCH /api/v1/users/{user_id}/role`
- **인증**: 필요 (`role=ADMIN`)
- **설명**: 관리자가 특정 회원의 권한(`PENDING`/`STAFF`/`ADMIN`)을 변경합니다.

**Path Parameter**: `user_id` (int)

**Request Body**
```json
{
  "role": "STAFF"
}
```

**Response `200 OK`**
```json
{
  "id": 5,
  "role": "STAFF"
}
```

**에러**
- `403` ADMIN이 아닌 사용자가 호출
- `404` 대상 유저 없음

---

### 2.7 마이페이지 조회
- **요구사항 ID**: REQ-USER-006
- **Method / Path**: `GET /api/v1/users/me`
- **인증**: 필요
- **설명**: 로그인한 사용자 본인의 정보를 조회합니다.

**Response `200 OK`**
```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "department": "DEV",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "PENDING"
}
```

---

### 2.8 회원 정보 수정 (Partial Update)
- **요구사항 ID**: REQ-USER-007
- **Method / Path**: `PATCH /api/v1/users/me`
- **인증**: 필요
- **설명**: 본인의 정보 중 `department`, `phone_number`만 부분 수정 가능합니다. (요구사항에 명시된 수정 가능 항목 외 필드는 무시/거부)

**Request Body** (둘 다 optional, 최소 1개 필요)
```json
{
  "department": "RESEARCH",
  "phone_number": "010-9876-5432"
}
```

**Response `200 OK`**
```json
{
  "id": 1,
  "department": "RESEARCH",
  "phone_number": "010-9876-5432",
  "updated_at": "2026-08-27T11:00:00"
}
```

**에러**
- `400` 수정 가능 항목 외 필드 요청 / 빈 바디
- `409` 전화번호 중복

---

### 2.9 비밀번호 변경
- **요구사항 ID**: REQ-USER-008, NFR-USER-002
- **Method / Path**: `PATCH /api/v1/users/me/password`
- **인증**: 필요
- **설명**: 기존 비밀번호 검증 후 신규 비밀번호로 변경합니다. 비밀번호 마스킹/보기 아이콘(NFR-USER-002)은 프론트엔드에서 처리합니다.

**Request Body**
```json
{
  "current_password": "securePassword123!",
  "new_password": "newSecurePassword456@"
}
```

**Response `204 No Content`**

**에러**
- `400` 기존 비밀번호 불일치, 신규 비밀번호가 정책에 맞지 않음

---

### 2.10 회원 탈퇴
- **요구사항 ID**: REQ-USER-009
- **Method / Path**: `DELETE /api/v1/users/me`
- **인증**: 필요
- **설명**: 본인 계정을 탈퇴 처리합니다. 요구사항에 따라 회원 관련 데이터를 DB에서 즉시 삭제합니다.

**Response `204 No Content`**

---

## 3. 비기능 요구사항(NFR) 대응
| ID | 내용 | 반영 방식 |
|---|---|---|
| NFR-USER-001 | JWT 인증/인가, Access 30분 / Refresh 7일, Refresh는 http_only 쿠키, payload는 `user_id`만 | 2.2, 2.3, 2.4 참고 |
| NFR-USER-002 | 비밀번호 입력 마스킹 + 보기 아이콘 | 프론트엔드 구현 사항 (API 스펙 영향 없음) |
| NFR-USER-003 | 모든 User API 3초 이내 응답 | 비동기(`async def`) 핸들러 + DB 쿼리 인덱스(예: `email`, `phone_number` unique index) 활용 |
