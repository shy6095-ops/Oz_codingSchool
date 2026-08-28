# 5일차 - 환자 관리 및 진료기록 API 설계

## 1. 개요

`5일차 - 진료기록 사용자 요구사항 정의서`를 기반으로 설계한 환자(Patient) / 진료기록(MedicalRecord) 도메인 API 명세서입니다. 데이터 모델은 `app/models/patient.py`, `app/models/medical_record.py`, `app/models/xray_image.py`에 이미 정의되어 있습니다.

- Base URL: `/api/v1`
- 인증: 모든 API는 로그인 필요 (`Authorization: Bearer <access_token>`, 4일차 User API의 `get_current_user` 의존성 재사용)
- 응답 포맷: `application/json` (X-Ray 업로드만 `multipart/form-data` 요청)
- 구현 구조: 기존 User 도메인과 동일하게 `apis(router) → services → repositories` 레이어 분리

### 공통 에러 응답


| 상태 코드 | 의미         |
| ----- | ---------- |
| 400   | 요청 값 검증 실패 |
| 401   | 인증 실패      |
| 404   | 리소스 없음     |


---

## 2. 엔드포인트 명세

### 2.1 환자 정보 등록

- **요구사항 ID**: REQ-PTNT-001
- **Method / Path**: `POST /api/v1/patients`

**Request Body**

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "010-1234-5678"
}
```

**Response `201 Created`**

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "010-1234-5678",
  "created_at": "2026-08-28T10:00:00",
  "updated_at": "2026-08-28T10:00:00"
}
```

---

### 2.2 환자 목록 조회

- **요구사항 ID**: REQ-PTNT-002
- **Method / Path**: `GET /api/v1/patients`

**Query Parameters**


| 이름        | 타입     | 필수  | 설명             |
| --------- | ------ | --- | -------------- |
| `search`  | string | N   | 이름 부분 일치 검색    |
| `gender`  | string | N   | `M` / `F`      |
| `min_age` | int    | N   | 나이 범위 필터 (이상)  |
| `max_age` | int    | N   | 나이 범위 필터 (이하)  |
| `offset`  | int    | N   | 기본값 0          |
| `limit`   | int    | N   | 기본값 20, 최대 100 |


**Response `200 OK`**

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "name": "홍길동",
      "age": 45,
      "gender": "M",
      "phone": "010-1234-5678",
      "created_at": "2026-08-28T10:00:00",
      "updated_at": "2026-08-28T10:00:00"
    }
  ]
}
```

---

### 2.3 환자 정보 상세 조회

- **요구사항 ID**: REQ-PTNT-003
- **Method / Path**: `GET /api/v1/patients/{patient_id}`

**Response `200 OK`**

```json
{
  "name": "홍길동",
  "gender": "M",
  "phone": "010-1234-5678",
  "age": 45
}
```

**에러**: `404` 해당 환자 없음

---

### 2.4 환자 정보 수정

- **요구사항 ID**: REQ-PTNT-004
- **Method / Path**: `PATCH /api/v1/patients/{patient_id}`
- **설명**: 이름, 연락처만 부분 수정 가능

**Request Body** (둘 다 optional, 최소 1개 필요)

```json
{
  "name": "홍길동2",
  "phone": "010-9999-8888"
}
```

**Response `200 OK`**: 수정된 환자 정보 전체 반환
**에러**: `400` 수정할 항목 없음, `404` 해당 환자 없음

---

### 2.5 환자 정보 삭제

- **요구사항 ID**: REQ-PTNT-005
- **Method / Path**: `DELETE /api/v1/patients/{patient_id}`
- **설명**: 해당 환자의 진료기록·X-Ray 이미지까지 함께 영구 삭제(cascade)한다.
- **구현 메모**: `Patient.medical_records`, `MedicalRecord.xray_images`, `MedicalRecord.ai_analysis_results` relationship에 `cascade="all, delete-orphan"` 옵션이 없으면 FK 제약(RESTRICT)에 걸려 삭제가 실패한다 — 서비스 레이어에서 자식 레코드를 함께 조회/삭제하거나 relationship cascade 옵션을 추가해야 함.

**Response `204 No Content`**
**에러**: `404` 해당 환자 없음

---

### 2.6 진료기록 등록 (X-Ray 이미지 업로드 포함)

- **요구사항 ID**: REQ-MDR-001
- **Method / Path**: `POST /api/v1/patients/{patient_id}/medical-records`
- **Content-Type**: `multipart/form-data`
- **설명**: 환자를 검색해서 선택한 뒤 진료 정보와 X-Ray 이미지를 함께 등록한다. 이미지는 서버 로컬 저장소(`media/xray/`)에 저장한다.

**Request (multipart/form-data)**


| 필드                  | 타입                | 필수  | 설명           |
| ------------------- | ----------------- | --- | ------------ |
| `chart_number`      | string (Form)     | Y   | 진료 차트 넘버     |
| `symptoms`          | string (Form)     | Y   | 진료된 증상       |
| `shooting_datetime` | datetime (Form)   | Y   | X-Ray 촬영 일시  |
| `xray_image`        | file (UploadFile) | Y   | 흉부 X-Ray 이미지 |


> ⚠️ **구현 시 주의**: FastAPI에서 `UploadFile`과 일반 필드를 같은 엔드포인트에서 받으려면, Pydantic 모델을 그대로 요청 바디로 못 쓰고 각 필드를 `Form(...)`으로 개별 선언하거나, Pydantic v2의 `Form` 지원(`Annotated[MyModel, Form()]`, 3.x 이상)을 써야 한다. 그냥 `BaseModel` 파라미터를 UploadFile과 함께 두면 422/500 에러가 남 (참고자료의 StackOverflow 이슈와 동일 케이스).

**Response `201 Created`**

```json
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "C-2026-001",
  "symptoms": "기침, 호흡곤란",
  "xray_image_url": "/media/xray/2026/08/28/uuid.jpg",
  "created_at": "2026-08-28T10:00:00"
}
```

**에러**: `404` 해당 환자 없음, `400` 이미지 누락/형식 오류

---

### 2.7 진료기록 목록 조회

- **요구사항 ID**: REQ-MDR-002
- **Method / Path**: `GET /api/v1/patients/{patient_id}/medical-records`
- **설명**: 증상은 100자 초과 시 뒤를 `...`으로 생략해서 반환한다.

**Response `200 OK`**

```json
{
  "items": [
    {
      "id": 1,
      "chart_number": "C-2026-001",
      "symptoms": "기침, 호흡곤란이 지속되어 내원함...",
      "created_at": "2026-08-28T10:00:00"
    }
  ]
}
```

---

### 2.8 진료기록 상세 조회

- **요구사항 ID**: REQ-MDR-003
- **Method / Path**: `GET /api/v1/medical-records/{record_id}`

**Response `200 OK`**

```json
{
  "id": 1,
  "chart_number": "C-2026-001",
  "symptoms": "기침, 호흡곤란이 지속되어 내원함",
  "xray_image_url": "/media/xray/2026/08/28/uuid.jpg",
  "created_at": "2026-08-28T10:00:00"
}
```

**에러**: `404` 해당 진료기록 없음

---

## 3. 비기능 요구사항(NFR) 대응


| ID           | 내용       | 반영 방식                                         |
| ------------ | -------- | --------------------------------------------- |
| NFR-PTNT-001 | 3초 이내 응답 | 비동기(`async def`) 핸들러 + 환자 검색용 인덱스(이름) 고려      |
| NFR-MDR-001  | 3초 이내 응답 | 비동기 핸들러 + 이미지 저장은 스트리밍 방식으로 처리해 대용량 파일 지연 최소화 |


