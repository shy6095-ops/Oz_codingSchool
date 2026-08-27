# 사용자 API 명세

## 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 인증 및 회원 관리 API |
| 설명 | 회원가입, JWT 로그인, 본인 정보 관리, 관리자 회원 관리 기능을 제공한다. |
| 기본 경로 | `/api/v1` |
| 인증 | 보호 API는 `Authorization: Bearer <access_token>`이 필요하다. |

### 공통 정책

- access token 유효기간은 30분(1,800초), refresh token 유효기간은 7일(604,800초)이다.
- JWT payload에는 최소 식별 정보인 `user_id`와 표준 만료시각 `exp`만 포함한다.
- refresh token은 JavaScript에서 접근할 수 없는 `HttpOnly; Secure; SameSite=Lax` 쿠키로만 전달한다.
- 가입 계정은 `PENDING` 권한으로 시작한다. `PENDING`은 마이페이지 외 업무 기능에 접근할 수 없다.
- 권한 값은 `PENDING`(대기자), `STAFF`(스태프), `ADMIN`(어드민)이다.
- 부서 값은 `RESEARCH`, `MEDICAL`, `DEV`, 성별 값은 `M`, `F`다.

### 공통 오류 응답

```json
{
  "detail": "오류 메시지"
}
```

입력값 형식이 맞지 않으면 FastAPI 표준 `422 Unprocessable Entity`를 반환한다.

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

## 2. 회원가입

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/signup` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 요청

`Content-Type: application/json`

```json
{
  "email": "employee@example.com",
  "password": "Aa1!secure",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "01012345678"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 고유 이메일 |
| password | string | Y | 8자 이상, 영문 대/소문자·숫자·특수문자 각 1개 이상 |
| name | string | Y | 1~20자 이름 |
| department | enum | Y | `RESEARCH`, `MEDICAL`, `DEV` |
| gender | enum | Y | `M`, `F` |
| phone_number | string | Y | 하이픈을 제외한 숫자 10~11자리, 고유값 |

### 성공

`201 Created`

```json
{
  "id": 1,
  "email": "employee@example.com",
  "name": "홍길동",
  "department": "DEV",
  "gender": "M",
  "phone_number": "01012345678",
  "role": "PENDING",
  "is_active": true
}
```

### 실패

- `409 Conflict`: 이메일 또는 휴대폰 번호가 이미 사용 중인 경우

## 3. 로그인

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/login` |
| 메서드 | `POST` |
| 인증 필요 여부 | N |

### 요청

`Content-Type: application/x-www-form-urlencoded`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| username | string | Y | 가입 이메일 |
| password | string | Y | 비밀번호 |

### 성공

`200 OK`

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "employee@example.com",
    "name": "홍길동",
    "department": "DEV",
    "gender": "M",
    "phone_number": "01012345678",
    "role": "PENDING",
    "is_active": true
  }
}
```

응답 헤더:

```http
Set-Cookie: refresh_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/users; Max-Age=604800
```

### 실패

- `401 Unauthorized`: `이메일 또는 비밀번호가 일치하지 않습니다.`
- `403 Forbidden`: `비활성화된 사용자입니다.`

## 4. 토큰 재발급 및 로그아웃

### refresh

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/refresh` |
| 메서드 | `POST` |
| 인증 필요 여부 | refresh cookie |

요청 본문은 없다. 브라우저는 로그인 응답의 `refresh_token` 쿠키를 자동 전송한다.

성공 시 `200 OK`와 로그인 성공과 같은 access-token JSON, 새 `Set-Cookie`를 반환한다. 기존 refresh token은 즉시 폐기되어 재사용할 수 없다.

실패 시 `401 Unauthorized`이며, refresh token까지 만료됐을 때 클라이언트는 로그인 화면으로 이동해야 한다.

### logout

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/logout` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y |

성공 시 `204 No Content`를 반환한다. 제출한 access token은 즉시 차단하고 refresh cookie를 삭제한다.

## 5. 마이페이지 API

### 내 정보 조회

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y |

성공 시 `200 OK`와 회원가입 성공 예시와 같은 사용자 객체를 반환한다.

### 내 정보 부분 수정

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

수정할 필드만 전송한다.

```json
{
  "department": "RESEARCH"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| department | enum | N | 변경할 부서 |
| phone_number | string | N | 변경할 휴대폰 번호 |

성공 시 `200 OK`와 변경된 사용자 객체를 반환한다. 중복 휴대폰 번호는 `409 Conflict`다.

### 비밀번호 변경

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/me/password` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | Y |

```json
{
  "current_password": "Aa1!secure",
  "new_password": "Bb2!changed"
}
```

성공 시 `204 No Content`를 반환한다. 기존 비밀번호 불일치는 `400 Bad Request`다.

### 회원탈퇴

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/users/me` |
| 메서드 | `DELETE` |
| 인증 필요 여부 | Y |

요청 본문은 사용하지 않는다. 성공 시 `204 No Content`를 반환하고 사용자, refresh session, access-token 차단 상태, 사용자가 업로드한 X-ray를 즉시 삭제한다. 공유 환자·진료기록은 삭제하지 않는다.

## 6. 관리자 회원 관리

두 API 모두 `ADMIN` 권한이 필요하며, 권한이 없으면 `403 Forbidden`을 반환한다.

### 회원 목록 조회

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/admin/users` |
| 메서드 | `GET` |
| 인증 필요 여부 | ADMIN |

| 쿼리 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| query | string | N | 이메일 또는 이름 부분 검색 |
| department | enum | N | 부서 필터 |

성공 시 `200 OK`와 사용자 객체 배열을 반환한다. 각 객체에는 고유 ID, 이메일, 이름, 부서, 성별, 휴대폰 번호, 권한, 활성 여부가 포함된다.

### 선택 회원 권한 변경

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `/api/v1/admin/users/roles` |
| 메서드 | `PATCH` |
| 인증 필요 여부 | ADMIN |

```json
{
  "user_ids": [2, 3],
  "role": "STAFF"
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_ids | integer array | Y | 하나 이상인 권한 변경 대상 ID |
| role | enum | Y | `PENDING`, `STAFF`, `ADMIN` |

성공 시 `200 OK`와 변경된 사용자 객체 배열을 반환한다. 존재하지 않는 대상은 `404 Not Found`, 자기 자신의 권한 변경은 `400 Bad Request`다.

## 7. 관리자 초기화와 로컬 DB

기본 DB 파일은 `db/ai_health.db`다. 첫 관리자 계정이 필요하면 실행 환경에 다음 값을 모두 설정한다. 설정값이 누락되면 자동 관리자는 생성하지 않는다.

```dotenv
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=Aa1!secure
BOOTSTRAP_ADMIN_NAME=관리자
BOOTSTRAP_ADMIN_PHONE_NUMBER=01011112222
BOOTSTRAP_ADMIN_DEPARTMENT=DEV
BOOTSTRAP_ADMIN_GENDER=M
```

운영 환경에서는 `ACCESS_TOKEN_SECRET_KEY`와 `REFRESH_TOKEN_SECRET_KEY`를 각각 충분히 긴 서로 다른 비밀값으로 설정한다. 설정하지 않은 개발 환경에서는 프로세스 시작 시 임시 키를 생성하므로 서버 재시작 후 기존 토큰은 유효하지 않다.
