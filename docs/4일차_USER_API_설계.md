# User API 명세서

## 1. 공통 사항

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 형식 | `application/json` |
| 인증 | `Authorization: Bearer {access_token}` |
| 액세스 토큰 | JWT, 30분 유효 |
| 리프레시 토큰 | JWT, 7일 유효, `HttpOnly` 쿠키로만 전달 |
| JWT 페이로드 | 사용자 식별자(`sub`, user_id), 만료 시각, 토큰 용도만 저장. 이메일·권한 등 개인정보는 저장하지 않음 |

### 공통 오류 형식

```json
{ "detail": "오류 메시지" }
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 오류 원인 |

### 사용자 값

| 구분 | 허용 값 | 설명 |
| --- | --- | --- |
| department | `MEDICAL`, `DEV`, `RESEARCH` | 의료, 개발, 연구 부서 |
| gender | `M`, `F` | 성별 |
| role | `PENDING`, `STAFF`, `ADMIN` | 대기자, 스태프, 관리자 |

---

# 2. 인증 API

## 2-1. 회원가입

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원가입 API |
| 설명 | 의료·개발·연구 부서의 사용자가 X-Ray AI 진단 서비스 계정을 생성한다. |
| Endpoint | `/api/v1/auth/signup` |
| Method | `POST` |
| 인증 필요 여부 | N |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | JSON 요청 본문 |

#### 본문 필드

```json
{
  "email": "hong@example.com",
  "password": "password1234",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678"
}
```

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 중복될 수 없는 이메일 |
| password | string | Y | 8~128자. 서버에는 해시값만 저장 |
| name | string | Y | 1~20자, 공백만 입력 불가 |
| department | string | Y | `MEDICAL`, `DEV`, `RESEARCH` 중 하나 |
| gender | string | Y | `M`, `F` 중 하나 |
| phone_number | string | Y | 중복될 수 없는 휴대폰 번호 |

#### 쿼리 파라미터

없음.

### Response

#### 성공: `201 Created`

```json
{
  "id": 1,
  "email": "hong@example.com",
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
| email, name, phone_number | string | 가입한 사용자 정보 |
| gender, department | string | 가입 시 선택한 성별·부서 |
| role | string | 서버가 기본값 `PENDING`으로 설정한 권한 |
| is_active | boolean | 활성 계정 여부 |
| created_at, updated_at | string | ISO 8601 UTC 일시 |

#### 실패

| 상태 코드 | 상황 | 예시 |
| --- | --- | --- |
| 409 | 이메일 또는 휴대폰 번호 중복 | `{ "detail": "이미 사용 중인 이메일입니다." }` |
| 422 | 필수값 누락, 이메일·열거형·길이 검증 실패 | FastAPI 검증 오류 |

### 비고

- 가입 직후 권한은 `PENDING`이다. 권한은 관리자가 변경한다.
- 가입 성공은 로그인 상태를 뜻하지 않는다.

---

## 2-2. 로그인

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그인 API |
| 설명 | 가입한 사용자가 이메일과 비밀번호로 로그인하고 인증 토큰을 발급받는다. |
| Endpoint | `/api/v1/auth/login` |
| Method | `POST` |
| 인증 필요 여부 | N |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | JSON 요청 본문 |

#### 본문 필드

```json
{ "email": "hong@example.com", "password": "password1234" }
```

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 가입 이메일 |
| password | string | Y | 비밀번호 |

#### 쿼리 파라미터

없음.

### Response

#### 성공: `200 OK`

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

응답 헤더에는 7일 유효한 리프레시 토큰 쿠키도 포함된다.

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | 이후 인증 헤더에 넣는 JWT 액세스 토큰 |
| token_type | string | `bearer` |
| expires_in | integer | 액세스 토큰 유효 시간(1800초) |

#### 실패

| 상태 코드 | 상황 | 예시 |
| --- | --- | --- |
| 401 | 이메일 또는 비밀번호 불일치, 비활성 계정 | `{ "detail": "이메일 또는 비밀번호가 일치하지 않습니다." }` |
| 422 | 필수값 누락 또는 이메일 형식 오류 | FastAPI 검증 오류 |

### 비고

- 리프레시 토큰은 JavaScript가 읽을 수 없는 `HttpOnly` 쿠키로 전달한다.
- 클라이언트는 액세스 토큰을 `Authorization: Bearer {access_token}`으로 보낸다.

---

## 2-3. 액세스 토큰 갱신

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 액세스 토큰 갱신 API |
| 설명 | 액세스 토큰이 만료되었을 때 유효한 리프레시 토큰으로 새 액세스 토큰을 발급한다. |
| Endpoint | `/api/v1/auth/refresh` |
| Method | `POST` |
| 인증 필요 여부 | 리프레시 토큰 쿠키 필요 |

### Request

#### Headers / Cookie

| Key | Value | 설명 |
| --- | --- | --- |
| Cookie | `refresh_token={token}` | 로그인 시 서버가 설정한 HttpOnly 쿠키 |

#### 본문 필드 및 쿼리 파라미터

없음.

### Response

#### 성공: `200 OK`

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 1800 }
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | 새 액세스 토큰 |
| token_type | string | `bearer` |
| expires_in | integer | 1800초 |

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 쿠키가 없거나 만료·위조·로그아웃 처리된 리프레시 토큰인 경우 |

### 비고

- 갱신 성공 시 리프레시 토큰도 새 쿠키로 교체한다.
- 리프레시 토큰까지 만료되면 다시 로그인해야 한다.

---

## 2-4. 로그아웃

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그아웃 API |
| 설명 | 로그인 세션의 리프레시 토큰을 폐기하고 쿠키를 삭제한다. |
| Endpoint | `/api/v1/auth/logout` |
| Method | `POST` |
| 인증 필요 여부 | 리프레시 토큰 쿠키 사용 |

### Request

#### Headers / 본문 / 쿼리 파라미터

`refresh_token` 쿠키 외 요청 값은 없다.

### Response

#### 성공: `204 No Content`

응답 본문은 없으며 리프레시 토큰 쿠키가 삭제된다.

### 비고

- 프런트엔드는 성공 후 로그인 페이지로 이동하고, 보관 중인 액세스 토큰을 제거한다.

---

# 3. 마이페이지 API

## 3-1. 내 정보 조회

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 내 정보 조회 API |
| 설명 | 로그인한 사용자가 자신의 마이페이지 정보를 조회한다. |
| Endpoint | `/api/v1/users/me` |
| Method | `GET` |
| 인증 필요 여부 | Y |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 로그인에서 발급받은 액세스 토큰 |

#### 본문 필드 및 쿼리 파라미터

없음.

### Response

#### 성공: `200 OK`

```json
{
  "id": 1, "email": "hong@example.com", "name": "홍길동",
  "phone_number": "01012345678", "gender": "M", "department": "MEDICAL",
  "role": "STAFF", "is_active": true,
  "created_at": "2026-08-27T12:00:00Z", "updated_at": "2026-08-27T12:00:00Z"
}
```

응답 필드는 회원가입 성공 응답과 같으며, 요구사항의 이름·이메일·부서·성별·휴대폰 번호·권한을 모두 포함한다.

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 인증 헤더가 없거나 액세스 토큰이 만료·위조된 경우 |

### 비고

- 사용자 ID나 이름을 요청에 넣지 않는다. 토큰의 user_id로 본인만 조회한다.

---

## 3-2. 내 정보 수정

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 정보 수정 API |
| 설명 | 로그인한 사용자가 부서와 휴대폰 번호를 부분 수정한다. |
| Endpoint | `/api/v1/users/me` |
| Method | `PATCH` |
| 인증 필요 여부 | Y |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 액세스 토큰 |
| Content-Type | application/json | JSON 요청 본문 |

#### 본문 필드

```json
{ "department": "RESEARCH", "phone_number": "01098765432" }
```

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| department | string | N | 변경할 부서 |
| phone_number | string | N | 변경할 휴대폰 번호. 다른 사용자와 중복 불가 |

#### 쿼리 파라미터

없음.

### Response

#### 성공: `200 OK`

내 정보 조회와 같은 사용자 정보를 반환한다.

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 변경할 필드가 없는 경우 |
| 401 | 인증 실패 |
| 409 | 이미 사용 중인 휴대폰 번호 |
| 422 | 부서·휴대폰 번호 형식 검증 실패 |

### 비고

- 요구사항에 따라 이메일·이름·성별·권한은 이 API에서 수정할 수 없다.

---

## 3-3. 비밀번호 변경

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 비밀번호 변경 API |
| 설명 | 현재 비밀번호를 검증한 뒤 새 비밀번호로 변경한다. |
| Endpoint | `/api/v1/users/me/password` |
| Method | `PATCH` |
| 인증 필요 여부 | Y |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 액세스 토큰 |
| Content-Type | application/json | JSON 요청 본문 |

#### 본문 필드

```json
{ "current_password": "password1234", "new_password": "newpassword1234" }
```

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 현재 비밀번호 |
| new_password | string | Y | 새 비밀번호(8~128자) |

#### 쿼리 파라미터

없음.

### Response

#### 성공: `204 No Content`

응답 본문이 없다.

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 현재 비밀번호 불일치 또는 기존 비밀번호와 동일한 새 비밀번호 |
| 401 | 인증 실패 |
| 422 | 필수값 누락 또는 비밀번호 길이 오류 |

### 비고

- 비밀번호 입력창의 마스킹은 프런트엔드 책임이며, 서버는 비밀번호를 평문으로 저장·반환하지 않는다.

---

## 3-4. 회원 탈퇴

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 탈퇴 API |
| 설명 | 로그인한 사용자의 회원 정보와 연결된 인증 정보를 즉시 삭제한다. |
| Endpoint | `/api/v1/users/me` |
| Method | `DELETE` |
| 인증 필요 여부 | Y |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 액세스 토큰 |

#### 본문 필드 및 쿼리 파라미터

없음.

### Response

#### 성공: `204 No Content`

응답 본문이 없다.

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 인증 실패 |

### 비고

- `is_active` 값만 바꾸는 소프트 삭제가 아니라 데이터베이스에서 실제 삭제한다.
- SQLAlchemy 관계 설정으로 연결된 업로드 이미지와 리프레시 토큰도 함께 삭제한다.

---

# 4. 관리자 API

## 4-1. 회원 목록 조회

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 목록 조회 API |
| 설명 | 관리자가 전체 회원을 검색·부서 필터와 함께 조회한다. |
| Endpoint | `/api/v1/admin/users` |
| Method | `GET` |
| 인증 필요 여부 | Y (관리자) |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | `ADMIN` 권한 사용자의 액세스 토큰 |

#### 본문 필드

없음.

#### 쿼리 파라미터

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| keyword | string | N | - | 이메일 또는 이름 부분 검색어 |
| department | string | N | - | 부서 필터 |
| page | integer | N | 1 | 페이지 번호(1 이상) |
| size | integer | N | 20 | 페이지당 개수(1~100) |

### Response

#### 성공: `200 OK`

```json
{
  "total": 1,
  "items": [{
    "id": 1, "email": "hong@example.com", "name": "홍길동",
    "phone_number": "01012345678", "gender": "M", "department": "MEDICAL",
    "role": "STAFF", "is_active": true,
    "created_at": "2026-08-27T12:00:00Z", "updated_at": "2026-08-27T12:00:00Z"
  }]
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| total | integer | 검색·필터 조건에 맞는 전체 회원 수 |
| items | array | 회원 목록. 각 항목은 ID, 이메일, 이름, 부서, 성별, 휴대폰 번호, 권한, 활성 여부를 포함 |

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 관리자 권한이 아닌 경우 |
| 422 | 페이지·부서 쿼리 값 검증 실패 |

### 비고

- 목록은 최신 ID 순으로 정렬한다.

---

## 4-2. 회원 권한 변경

### API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 권한 변경 API |
| 설명 | 관리자가 대상 회원의 권한을 `PENDING`, `STAFF`, `ADMIN` 중 하나로 변경한다. |
| Endpoint | `/api/v1/admin/users/{user_id}/role` |
| Method | `PATCH` |
| 인증 필요 여부 | Y (관리자) |

### Request

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `{access_token}` | 관리자 액세스 토큰 |
| Content-Type | application/json | JSON 요청 본문 |

#### Path / 본문 필드

| 위치 | 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- | --- |
| Path | user_id | integer | Y | 권한을 바꿀 회원 ID |
| Body | role | string | Y | `PENDING`, `STAFF`, `ADMIN` 중 하나 |

```json
{ "role": "STAFF" }
```

#### 쿼리 파라미터

없음.

### Response

#### 성공: `200 OK`

변경된 권한을 포함한 사용자 정보를 반환한다.

#### 실패

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 인증 실패 |
| 403 | 관리자 권한 없음 |
| 404 | 대상 회원 없음 |
| 422 | `user_id` 또는 role 값 검증 실패 |

### 비고

- `PENDING`은 마이페이지만, `STAFF`는 X-Ray 결과 조회·작성·수정, `ADMIN`은 전체 메뉴에 접근할 수 있도록 후속 기능에서 권한을 적용한다.
- 모든 API는 일반적인 환경에서 3초 이내 응답을 목표로 한다.
