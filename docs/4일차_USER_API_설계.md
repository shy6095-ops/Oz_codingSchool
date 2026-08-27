# User API 명세서

## 공통 사항

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 형식 | JSON (`application/json`) |
| 인증 방식 | Bearer JWT 액세스 토큰 |
| 날짜 형식 | ISO 8601 UTC 예: `2026-08-27T12:00:00Z` |

### 공통 오류 응답 형식

별도 응답 예시가 없는 오류도 아래 형식을 따른다.

```json
{
  "detail": "오류 메시지"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 오류 원인을 설명하는 메시지 |

---

# 1. 회원가입 API

## 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원가입 API |
| 설명 | 신규 사용자가 이메일, 비밀번호, 이름, 전화번호, 성별, 부서를 입력하여 계정을 생성한다. |
| 엔드포인트(Endpoint) | `/api/v1/users` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |

## 2. 요청(Request)

### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 본문이 JSON 형식임을 나타낸다. |

### 본문 필드

```json
{
  "email": "example@example.com",
  "password": "password1234",
  "name": "홍길동",
  "phone_number": "01012345678",
  "gender": "M",
  "department": "MEDICAL"
}
```

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일. 이메일 형식이어야 하며 다른 사용자와 중복될 수 없다. |
| password | string | Y | 비밀번호. 8자 이상으로 입력하며 서버에는 해시된 값으로 저장한다. |
| name | string | Y | 사용자 이름. 공백만으로 입력할 수 없으며 최대 20자이다. |
| phone_number | string | Y | 사용자 전화번호. 다른 사용자와 중복될 수 없다. |
| gender | string | Y | 성별. `M` 또는 `F` 중 하나를 입력한다. |
| department | string | Y | 소속 부서. `MEDICAL`, `DEV`, `RESEARCH` 중 하나를 입력한다. |

### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | 회원가입 API는 쿼리 파라미터를 사용하지 않는다. |

## 3. 응답(Response)

### 성공

- `201 Created`

```json
{
  "id": 1,
  "email": "example@example.com",
  "name": "홍길동",
  "phone_number": "01012345678",
  "gender": "M",
  "department": "MEDICAL",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-08-27T12:00:00Z",
  "updated_at": "2026-08-27T12:00:00Z"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 생성된 사용자 ID |
| email | string | 가입한 사용자 이메일 |
| name | string | 가입한 사용자 이름 |
| phone_number | string | 가입한 사용자 전화번호 |
| gender | string | 성별 (`M`, `F`) |
| department | string | 소속 부서 (`MEDICAL`, `DEV`, `RESEARCH`) |
| role | string | 사용자 권한. 회원가입 시 서버가 `PENDING`으로 설정한다. |
| is_active | boolean | 활성 계정 여부 |
| created_at | string | 계정 생성 일시(ISO 8601 UTC) |
| updated_at | string / null | 마지막 정보 수정 일시(ISO 8601 UTC) |

### 실패

- `400 Bad Request` — 요청 값의 형식이 잘못되었거나 비밀번호 정책을 만족하지 않는 경우

```json
{
  "detail": "비밀번호는 8자 이상이어야 합니다."
}
```

- `409 Conflict` — 이미 가입된 이메일인 경우

```json
{
  "detail": "이미 사용 중인 이메일입니다."
}
```

- `422 Unprocessable Entity` — 필수 필드가 누락되었거나 이메일 형식이 올바르지 않은 경우

```json
{
  "detail": "email은 올바른 이메일 형식이어야 합니다."
}
```

## 4. 비고

- 비밀번호 원문은 응답하거나 데이터베이스에 평문으로 저장하지 않는다.
- 회원가입 성공만으로 로그인 상태가 되지는 않는다. 로그인 API에서 별도로 토큰을 발급받는다.
- `role`은 사용자가 입력하지 않으며 서버가 기본값 `PENDING`으로 설정한다.

---

# 2. 내 정보 조회 API

## 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 조회 API |
| 설명 | 로그인한 사용자가 자신의 계정 정보를 조회한다. |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

## 2. 요청(Request)

### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 로그인 후 발급받은 JWT 액세스 토큰 |

### 본문 필드

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | GET 요청이므로 요청 본문을 사용하지 않는다. |

### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | 내 정보 조회 API는 쿼리 파라미터를 사용하지 않는다. |

## 3. 응답(Response)

### 성공

- `200 OK`

```json
{
  "id": 1,
  "email": "example@example.com",
  "name": "홍길동",
  "phone_number": "01012345678",
  "gender": "M",
  "department": "MEDICAL",
  "role": "PENDING",
  "is_active": true,
  "created_at": "2026-08-27T12:00:00Z",
  "updated_at": "2026-08-27T12:00:00Z"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 로그인한 사용자 ID |
| email | string | 로그인한 사용자 이메일 |
| name | string | 로그인한 사용자 이름 |
| phone_number | string | 로그인한 사용자 전화번호 |
| gender | string | 성별 (`M`, `F`) |
| department | string | 소속 부서 |
| role | string | 사용자 권한 (`PENDING`, `STAFF`, `ADMIN`) |
| is_active | boolean | 활성 계정 여부 |
| created_at | string | 계정 생성 일시(ISO 8601 UTC) |
| updated_at | string / null | 마지막 정보 수정 일시(ISO 8601 UTC) |

### 실패

- `401 Unauthorized` — Authorization 헤더가 없거나 토큰이 유효하지 않은 경우

```json
{
  "detail": "인증 정보가 없거나 유효하지 않습니다."
}
```

- `404 Not Found` — 토큰의 사용자가 존재하지 않거나 탈퇴 처리된 경우

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

## 4. 비고

- 비밀번호, 비밀번호 해시 등 민감 정보는 응답에 포함하지 않는다.
- `/me`는 인증 토큰의 사용자 정보를 기준으로 처리하므로 사용자 ID를 경로에 전달하지 않는다.

---

# 3. 내 정보 수정 API

## 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 수정 API |
| 설명 | 로그인한 사용자가 자신의 이름 또는 비밀번호를 수정한다. |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

## 2. 요청(Request)

### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 본문이 JSON 형식임을 나타낸다. |
| Authorization | Bearer `{access_token}` | 로그인 후 발급받은 JWT 액세스 토큰 |

### 본문 필드

```json
{
  "name": "김길동",
  "password": "newpassword1234"
}
```

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
| --- | --- | --- | --- |
| name | string | N | 변경할 사용자 이름. 공백만으로 입력할 수 없다. |
| password | string | N | 변경할 비밀번호. 8자 이상이어야 하며 해시하여 저장한다. |

### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | 내 정보 수정 API는 쿼리 파라미터를 사용하지 않는다. |

## 3. 응답(Response)

### 성공

- `200 OK`

```json
{
  "id": 1,
  "email": "example@example.com",
  "name": "김길동",
  "phone_number": "01012345678",
  "gender": "M",
  "department": "MEDICAL",
  "role": "PENDING",
  "updated_at": "2026-08-27T13:00:00Z"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 수정된 사용자 ID |
| email | string | 사용자 이메일. 이 API에서는 변경하지 않는다. |
| name | string | 수정 후 사용자 이름 |
| phone_number | string | 사용자 전화번호. 이 API에서는 변경하지 않는다. |
| gender | string | 성별. 이 API에서는 변경하지 않는다. |
| department | string | 소속 부서. 이 API에서는 변경하지 않는다. |
| role | string | 사용자 권한. 이 API에서는 변경하지 않는다. |
| updated_at | string / null | 정보 수정 일시(ISO 8601 UTC) |

### 실패

- `400 Bad Request` — 수정할 필드가 없거나 비밀번호 정책을 만족하지 않는 경우

```json
{
  "detail": "수정할 정보가 없습니다."
}
```

- `401 Unauthorized` — Authorization 헤더가 없거나 토큰이 유효하지 않은 경우

```json
{
  "detail": "인증 정보가 없거나 유효하지 않습니다."
}
```

- `404 Not Found` — 토큰의 사용자가 존재하지 않거나 탈퇴 처리된 경우

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

- `422 Unprocessable Entity` — 필드 타입이 올바르지 않거나 유효성 검사를 통과하지 못한 경우

```json
{
  "detail": "name은 빈 문자열일 수 없습니다."
}
```

## 4. 비고

- 부분 수정 API이므로 `name`, `password` 중 하나 이상을 전달해야 한다.
- 이메일 변경은 본 과제 범위에서 제외한다. 이메일 변경이 필요하면 본인 확인 절차를 포함한 별도 API로 설계한다.
- 비밀번호 변경 후 기존 액세스 토큰을 무효화할지는 인증 정책에 따라 결정한다.

---

# 4. 회원탈퇴 API

## 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원탈퇴 API |
| 설명 | 로그인한 사용자가 자신의 계정을 탈퇴 처리한다. |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |

## 2. 요청(Request)

### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 로그인 후 발급받은 JWT 액세스 토큰 |

### 본문 필드

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | 회원탈퇴 API는 요청 본문을 사용하지 않는다. |

### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | N | 회원탈퇴 API는 쿼리 파라미터를 사용하지 않는다. |

## 3. 응답(Response)

### 성공

- `204 No Content`

성공 시 응답 본문을 반환하지 않는다.

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| 없음 | - | `204 No Content` 응답은 본문을 포함하지 않는다. |

### 실패

- `401 Unauthorized` — Authorization 헤더가 없거나 토큰이 유효하지 않은 경우

```json
{
  "detail": "인증 정보가 없거나 유효하지 않습니다."
}
```

- `404 Not Found` — 토큰의 사용자가 존재하지 않거나 이미 탈퇴 처리된 경우

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

## 4. 비고

- 본 명세에서는 탈퇴 성공 시 `204 No Content`를 반환하며, 토큰이나 사용자 정보를 반환하지 않는다.
- 실제 구현은 사용자 레코드를 삭제하지 않고 `is_active` 값을 `false`로 변경한다.
- 탈퇴한 사용자는 이후 인증된 API를 사용할 수 없다. 토큰 자체를 블랙리스트에 저장하지는 않지만, 비활성 사용자 조회에서 제외되어 접근이 차단된다.
