# 사용자 인증 및 권한 관리 설계

## 목표

SQLite 기반 비동기 FastAPI 사용자 API를 추가해 회원가입, JWT 인증, 내 정보 관리, 관리자 회원 관리 요구사항을 충족한다.

## 범위

- 포함: REQ-USER-001~009, NFR-USER-001~003에 필요한 사용자 API, SQLite, 사용자 화면의 계약 보정, API 명세, 자동 테스트.
- 제외: 환자, 진료 기록, X-ray, AI 예측 및 기존 `/practice_api` 예제의 변경.

## 데이터와 시작 방식

- 기본 DB는 `db/ai_health.db`이며 URL은 환경변수 `DATABASE_URL`로 교체할 수 있다.
- FastAPI lifespan은 비동기 SQLAlchemy로 `Base.metadata.create_all`을 실행하고 SQLite foreign key와 WAL을 활성화한다.
- 가입 사용자는 항상 `PENDING`, 활성 상태로 생성한다.
- `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PHONE_NUMBER`, `BOOTSTRAP_ADMIN_DEPARTMENT`, `BOOTSTRAP_ADMIN_GENDER`가 모두 설정됐을 때만 존재하지 않는 이메일의 `ADMIN` 계정을 한 번 생성한다. 소스 코드에는 관리자 자격증명을 넣지 않는다.

## 인증

- access token은 1,800초, refresh token은 604,800초 동안 유효하다.
- 두 JWT는 서로 다른 비밀키로 서명하며 payload에는 `user_id`와 표준 `exp`만 둔다. 토큰 회전을 위해 서명된 JWT 헤더에 난수 `kid`를 둔다.
- access token은 JSON의 `access_token`으로, refresh token은 `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/users` 쿠키로 전달한다.
- refresh token의 SHA-256 digest는 DB 세션 테이블에 저장한다. refresh는 세션을 회전시키며, logout과 회원탈퇴는 해당 세션을 폐기한다.
- logout은 제출된 access token digest를 만료 시각까지 차단 목록에 기록해 즉시 재사용을 막는다.

## 인가와 삭제 경계

- 모든 보호 API는 bearer access token, 활성 사용자 여부, access token 차단 목록을 검사한다.
- `PENDING`은 본인 조회·수정·비밀번호 변경·탈퇴와 인증 API만 사용할 수 있다. `ADMIN`만 회원 목록 및 권한 변경을 사용할 수 있다.
- 회원탈퇴는 사용자, refresh 세션, access-token 차단 항목 및 사용자가 업로드한 X-ray를 즉시 삭제한다. 공유 환자와 진료 기록은 사용자 소유 데이터가 아니므로 보존한다.

## API 계약

| 메서드 | 경로 | 권한 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/users/signup` | 공개 | 가입 |
| POST | `/api/v1/users/login` | 공개 | access/refresh 발급 |
| POST | `/api/v1/users/refresh` | refresh cookie | access 재발급 및 refresh 회전 |
| POST | `/api/v1/users/logout` | 로그인 | 토큰 폐기 |
| GET/PATCH/DELETE | `/api/v1/users/me` | 로그인 | 내 정보 조회/부분 수정/탈퇴 |
| PATCH | `/api/v1/users/me/password` | 로그인 | 기존 비밀번호 검증 후 변경 |
| GET | `/api/v1/admin/users` | ADMIN | 이름/이메일 검색 및 부서 필터 목록 |
| PATCH | `/api/v1/admin/users/roles` | ADMIN | 선택 회원 권한 일괄 변경 |

## 화면과 문서

- 기존 사용자 화면의 프런트 값은 API enum 값으로 정규화한다.
- 로그인·가입·비밀번호 변경 입력에는 보기/숨기기 버튼을 둔다.
- 관리자 표에는 요구된 성별을 추가하고 선택 체크박스와 상단 일괄 권한 변경을 제공한다.
- `docs/api/user-api.md`에는 각 API의 요청, 성공/실패 응답, 쿠키, 권한, 만료 정책을 기록한다.

## 검증

- 테스트는 임시 SQLite 파일과 비동기 HTTP 클라이언트로 회원가입, 중복 검증, 로그인/refresh 회전, 권한, 부분 수정, 비밀번호 변경, 즉시 로그아웃 차단, 탈퇴 cascade를 검증한다.
- 비동기 DB I/O 외에 블로킹 I/O를 추가하지 않으며, Argon2 해싱·검증은 `asyncio.to_thread`로 분리한다. API 처리 시간은 로컬 통합 테스트에서 3초 이내인지 확인한다.
