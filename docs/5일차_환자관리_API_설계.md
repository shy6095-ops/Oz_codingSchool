# 5일차 환자 관리 API 설계

## 1. 개요

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 인증 필요 여부 | Y (`Authorization: Bearer <access_token>`) |
| 저장소 | MySQL 데이터베이스, 서버 로컬 `media/xrays/` |
| 처리 방식 | DB I/O는 SQLAlchemy `AsyncSession`, 이미지 파일 I/O는 `asyncio.to_thread` |

성별 값은 `M`(남성), `F`(여성)만 사용한다. 모든 시간은 ISO 8601 형식으로 반환한다.

## 2. 환자 API

### 2.1 환자 등록 — REQ-PTNT-001

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/patients` |
| Content-Type | `application/json` |
| 성공 | `201 Created` |

의료 부서(`MEDICAL`) 사용자만 등록할 수 있다. 로그인하지 않은 요청은 `401 Unauthorized`, 다른 부서는 `403 Forbidden`을 반환한다.

요청 본문:

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone_number": "01012345678"
}
```

필수 필드: `name`(최대 30자), `age`(0~130), `gender`(`M`/`F`), `phone_number`(최대 20자).

성공 응답:

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone_number": "01012345678",
  "created_at": "2026-08-28T10:00:00Z",
  "updated_at": null
}
```

### 2.2 환자 목록 조회 — REQ-PTNT-002

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/patients` |
| 성공 | `200 OK` |

선택 쿼리 파라미터:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `name` | string | 환자 이름 부분 검색 |
| `gender` | `M` / `F` | 성별 필터 |
| `min_age` | integer | 최소 나이 (0~130) |
| `max_age` | integer | 최대 나이 (0~130) |
| `page` | integer | 페이지 번호, 기본값 `1` |
| `size` | integer | 페이지 크기(1~100), 기본값 `20` |

예시: `GET /api/v1/patients?name=홍&gender=M&min_age=20&max_age=60`

성공 응답은 `total`, `page`, `size`, `items`를 포함한다. `items`의 각 항목은 `id`, `name`, `age`, `gender`, `phone_number`, `created_at`, `updated_at`을 포함한다. `min_age`가 `max_age`보다 크면 `422 Unprocessable Entity`를 반환한다.

### 2.3 환자 상세 조회 — REQ-PTNT-003

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/patients/{patient_id}` |
| 성공 | `200 OK` |
| 실패 | `404 Not Found` — 존재하지 않는 환자 |

응답 필드는 환자 등록 성공 응답과 같다.

### 2.4 환자 부분 수정 — REQ-PTNT-004

| 항목 | 내용 |
| --- | --- |
| Endpoint | `PATCH /api/v1/patients/{patient_id}` |
| Content-Type | `application/json` |
| 성공 | `200 OK` |

수정 가능한 필드는 이름과 연락처이며, 둘 중 하나 이상을 보낸다.

```json
{
  "name": "김길동",
  "phone_number": "01098765432"
}
```

존재하지 않는 환자는 `404 Not Found`, 비어 있는 부분 수정 요청은 `422 Unprocessable Entity`를 반환한다.

### 2.5 환자 삭제 — REQ-PTNT-005

| 항목 | 내용 |
| --- | --- |
| Endpoint | `DELETE /api/v1/patients/{patient_id}` |
| 요청 본문 | 없음 |
| 성공 | `204 No Content` |

삭제 시 해당 환자의 진료기록, X-Ray 이미지 DB 행, AI 분석 결과 DB 행을 삭제하고 연결된 `media/xrays/` 파일도 비동기로 삭제한다. 존재하지 않는 환자는 `404 Not Found`를 반환한다.

## 3. 진료기록 API

### 3.1 진료기록 등록 — REQ-MDR-001

| 항목 | 내용 |
| --- | --- |
| Endpoint | `POST /api/v1/patients/{patient_id}/medical-records` |
| Content-Type | `multipart/form-data` |
| 성공 | `201 Created` |

의료 부서(`MEDICAL`) 사용자만 등록할 수 있다.

필수 form-data 필드 (`patient_id`는 경로 파라미터):

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `chart_number` | string | 차트 번호, 최대 50자 |
| `symptoms` | string | 진료 증상 |

선택 form-data 필드:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `xray_image` | file | JPG, JPEG 또는 PNG 이미지 |

성공 응답:

```json
{
  "id": 10,
  "patient_id": 1,
  "chart_number": "CH-20260828-001",
  "symptoms": "기침과 발열",
  "created_at": "2026-08-28T10:10:00Z",
  "xray_image_url": null
}
```

증상은 필수이며 X-Ray 이미지는 선택이다. 이미지를 업로드하면 파일명은 UUID로 새로 생성되어 서버 로컬 `media/xrays/`에 저장되고 `xray_image_url`에 경로가 반환된다. 이미지를 보내지 않으면 `xray_image_url`은 `null`이다. 빈 파일, 이미지 형식이 아닌 파일, 지원하지 않는 확장자는 `422 Unprocessable Entity`를 반환한다. 환자가 없으면 `404 Not Found`를 반환한다.

### 3.2 환자별 진료기록 목록 조회 — REQ-MDR-002

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/patients/{patient_id}/medical-records?page=1&size=20` |
| 성공 | `200 OK` |

성공 응답은 최신 진료기록부터 `total`, `page`, `size`, `items` 형태로 반환한다. `items`의 각 항목은 `id`, `patient_id`, `chart_number`, `symptoms`, `created_at`을 포함한다. 화면에서는 `symptoms`가 100자를 넘으면 말줄임표로 표시한다. 환자가 없으면 `404 Not Found`를 반환한다.

### 3.3 진료기록 상세 조회 — REQ-MDR-003

| 항목 | 내용 |
| --- | --- |
| Endpoint | `GET /api/v1/patients/{patient_id}/medical-records/{record_id}` |
| 성공 | `200 OK` |
| 실패 | `404 Not Found` — 존재하지 않는 진료기록 |

응답에는 `id`, `patient_id`, `chart_number`, `symptoms`, `created_at`, `xray_image_url`이 포함된다. 이미지가 없는 기록의 `xray_image_url`은 `null`이며, 이미지가 있으면 `/media/` 정적 경로로 바로 조회할 수 있다.

## 4. 공통 오류 형식

```json
{
  "detail": "환자를 찾을 수 없습니다."
}
```

입력값 형식 또는 필수값이 잘못된 경우 FastAPI 기본 검증 형식으로 `422 Unprocessable Entity`를 반환한다.

```json
{
  "detail": [
    {
      "loc": ["body", "age"],
      "msg": "Input should be less than or equal to 130",
      "type": "less_than_equal"
    }
  ]
}
```

## 5. 비고

- 모든 환자·진료기록 API는 유효한 Bearer 액세스 토큰이 필요하다. 등록 API는 의료 부서 사용자만 사용할 수 있다.
- DB와 파일 저장 작업은 비동기 흐름으로 처리하며, 파일 저장·삭제처럼 동기 파일 시스템 호출이 필요한 부분은 이벤트 루프를 막지 않도록 `asyncio.to_thread`를 사용한다.
- NFR-PTNT-001, NFR-MDR-001의 3초 응답 목표를 위해 목록 조회는 필요한 범위만 조회하고, 이미지 파일은 응답 본문에 포함하지 않고 URL만 반환한다.
