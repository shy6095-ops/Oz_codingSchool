# 4일차 User 사용자 요구사항 API 정의서

## 1. 개요
본 문서는 요구사항 정의서를 바탕으로 FastAPI 프레임워크와 Pydantic 모델을 활용하여 설계된 RESTful API 명세서입니다. 비기능 요구사항(JWT 인증/인가 로직, http_only 쿠키 보안, 3초 이내 응답 등)을 충족하도록 구성되었습니다.

---

## 2. API 엔드포인트 명세

### 2.1. 회원 가입 (Sign Up)
*   **요구사항 ID:** REQ-USER-001
*   **Method & Path:** `POST /api/v1/users/signup`
*   **Description:** 사내 의료진 및 개발 실무진의 회원가입을 처리합니다.
*   **Request Body (application/json - Pydantic Model):**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123!",
      "name": "홍길동",
      "department": "개발",     // Enum: ["연구", "의료", "개발"]
      "gender": "M",          // Enum: ["M", "F"]
      "phone": "010-1234-5678"
    }
    ```
*   **Response:** `201 Created`
    ```json
    {
      "message": "회원가입이 완료되었습니다.",
      "user_id": 1
    }
    ```

### 2.2. 로그인 (Login)
*   **요구사항 ID:** REQ-USER-002, NFR-USER-001
*   **Method & Path:** `POST /api/v1/auth/login`
*   **Description:** 이메일과 비밀번호로 로그인 인증을 수행합니다.
*   **Request Body (application/json):**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123!"
    }
    ```
*   **Response:** `200 OK`
    *   **Body:**
        ```json
        {
          "access_token": "eyJhbGci...",
          "token_type": "bearer",
          "expires_in": 1800  // 30분
        }
        ```
    *   **Set-Cookie:** `refresh_token=eyJhbGci...; HttpOnly; Path=/; Max-Age=604800` (7일)
    *   *참고: JWT 페이로드에는 최소 식별 정보인 `user_id`만 포함됩니다.*

### 2.3. 로그아웃 (Logout)
*   **요구사항 ID:** REQ-USER-003
*   **Method & Path:** `POST /api/v1/auth/logout`
*   **Description:** 로그인 상태를 해제하고 클라이언트의 쿠키를 삭제합니다.
*   **Header:** `Authorization: Bearer <access_token>`
*   **Response:** `200 OK`
    *   **Set-Cookie:** `refresh_token=; HttpOnly; Path=/; Max-Age=0`

### 2.4. 회원 목록 조회 (Admin Only)
*   **요구사항 ID:** REQ-USER-004
*   **Method & Path:** `GET /api/v1/users`
*   **Description:** 관리자 권한으로 전체 회원 목록을 조회하고 검색/필터링합니다. FastAPI의 `Query` 매개변수를 활용합니다.
*   **Header:** `Authorization: Bearer <access_token>` (어드민 권한 필수)
*   **Query Parameters (Pydantic Model 활용 가능):**
    *   `search` (string, optional): 이메일 또는 이름 검색
    *   `department` (string, optional): 부서 필터링 (연구, 의료, 개발)
*   **Response:** `200 OK`
    ```json
    [
      {
        "user_id": 1,
        "email": "user@example.com",
        "name": "홍길동",
        "department": "개발",
        "gender": "M",
        "phone": "010-1234-5678",
        "is_active": true
      }
    ]
    ```

### 2.5. 회원 권한 변경 (Admin Only)
*   **요구사항 ID:** REQ-USER-005
*   **Method & Path:** `PATCH /api/v1/users/{user_id}/role`
*   **Description:** 관리자가 특정 회원의 권한을 변경합니다.
*   **Header:** `Authorization: Bearer <access_token>`
*   **Path Parameter:** `user_id` (integer)
*   **Request Body:**
    ```json
    {
      "role": "스태프"  // Enum: ["대기자", "스태프", "어드민"]
    }
    ```
*   **Response:** `200 OK`

### 2.6. 마이페이지 조회
*   **요구사항 ID:** REQ-USER-006
*   **Method & Path:** `GET /api/v1/users/me`
*   **Description:** 현재 로그인한 사용자의 본인 정보를 조회합니다.
*   **Header:** `Authorization: Bearer <access_token>`
*   **Response:** `200 OK`
    ```json
    {
      "name": "홍길동",
      "email": "user@example.com",
      "department": "개발",
      "gender": "M",
      "phone": "010-1234-5678",
      "role": "대기자"
    }
    ```

### 2.7. 회원 정보 수정 (Partial Update)
*   **요구사항 ID:** REQ-USER-007
*   **Method & Path:** `PATCH /api/v1/users/me`
*   **Description:** 본인의 정보를 선택적으로(Partial) 수정합니다.
*   **Header:** `Authorization: Bearer <access_token>`
*   **Request Body (Optional Fields):**
    ```json
    {
      "department": "연구",
      "phone": "010-9876-5432"
    }
    ```
*   **Response:** `200 OK`

### 2.8. 비밀번호 변경
*   **요구사항 ID:** REQ-USER-008, NFR-USER-002
*   **Method & Path:** `PATCH /api/v1/users/me/password`
*   **Description:** 기존 비밀번호 검증 후 새로운 비밀번호로 변경합니다. (클라이언트 단에서 NFR-USER-002 입력 보안 처리)
*   **Header:** `Authorization: Bearer <access_token>`
*   **Request Body:**
    ```json
    {
      "old_password": "securepassword123!",
      "new_password": "newSecurePassword456@"
    }
    ```
*   **Response:** `200 OK`

### 2.9. 회원 탈퇴
*   **요구사항 ID:** REQ-USER-009
*   **Method & Path:** `DELETE /api/v1/users/me`
*   **Description:** 회원 탈퇴 처리를 진행하며 DB에서 관련 정보를 즉시 삭제합니다.
*   **Header:** `Authorization: Bearer <access_token>`
*   **Response:** `204 No Content`

---

## 3. 비기능 요구사항(NFR) 준수 사항
1.  **NFR-USER-001 (인증/인가):** Access Token은 Authorization 헤더로, Refresh Token은 탈취 방지를 위해 `HttpOnly` 쿠키로 발급 및 검증되도록 설계되었습니다. Payload에는 `user_id`만 포함하여 경량화합니다.
2.  **NFR-USER-002 (비밀번호 보안):** API 스펙 외에 프론트엔드 단에서 마스킹 및 보기 아이콘 기능이 구현되어야 합니다.
3.  **NFR-USER-003 (API 성능):** 모든 API 엔드포인트는 비동기(`async def`) 기반으로 작성되어 병목을 최소화하고 3초 이내 응답을 보장하도록 구현해야 합니다.

---

## 4. Git Branch 병합 가이드

해당 문서를 `main` 또는 `develop` 브랜치에 병합하기 위한 Git 전략입니다. 
터미널(또는 Git Bash)에서 다음 명령어를 순서대로 실행하세요.

```bash
# 1. 작업 중인 Feature 브랜치에 작성된 문서 커밋
git add 4일차_유저_사용자_정의서_hans.md
git commit -m "docs: 4일차 사용자 요구사항 API 명세서 작성"

# 2. 타겟 브랜치(develop 또는 main)로 이동 및 최신화
git checkout develop
git pull origin develop

# 3. 브랜치 병합 (Merge)
git merge <본인이 작업한 feature 브랜치명>

# 4. 원격 저장소로 푸시
git push origin develop
```
*(※ 만약 PR(Pull Request) 기반의 협업을 진행 중이라면, 원격 저장소(GitHub/GitLab)에서 2~4번 과정 대신 작업 브랜치를 푸시한 후 PR을 생성하여 리뷰 후 병합하는 것을 권장합니다.)*
