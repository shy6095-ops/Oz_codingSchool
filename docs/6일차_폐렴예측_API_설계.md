# 6일차 폐렴 예측 API 설계

## 1. 목적

저장된 진료 기록의 X-ray 이미지를 `SimpleCNN` 모델로 분석하여 폐렴 예측 결과를 조회한다.
동일한 진료 기록에 동일한 모델로 이미 예측한 결과가 있다면 모델을 다시 실행하지 않고 저장된 결과를 반환한다.

## 2. 공통 사항

- Base URL: `/api/v1`
- 인증: `Authorization: Bearer <access_token>` 헤더가 필요하다.
- 권한: 승인된(`STAFF` 또는 `ADMIN`) 의료(`MEDICAL`), 개발(`DEV`), 연구(`RESEARCH`) 부서 사용자만 호출할 수 있다.
- 모델명: `SimpleCNN`
- 모델 입력: X-ray 이미지를 흑백 128 × 128으로 변환한 뒤 모델에 전달한다.
- Heatmap: 선택 기능이다. 현재 생성하지 않으므로 응답에서는 `null`로 반환한다.

## 3. API 명세

### REQ-PRED-001: 폐렴 예측 실행

저장된 진료 기록의 X-ray 이미지로 폐렴 예측을 수행한다.

```http
POST /api/v1/medical-records/{record_id}/predict
Authorization: Bearer <access_token>
```

#### Path parameter

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `record_id` | integer | 예측할 진료 기록 ID |

#### 처리 흐름

1. 사용자의 로그인·권한을 확인한다.
2. 해당 진료 기록과 저장된 X-ray 이미지를 조회한다.
3. 같은 `record_id`와 `ai_model=SimpleCNN` 조합의 결과가 있으면 기존 결과를 반환한다.
4. 결과가 없으면 X-ray 파일을 읽고 모델로 예측한다.
5. 예측 결과를 `ai_analysis_results` 테이블에 저장한 뒤 반환한다.

#### 성공 응답: `200 OK`

```json
{
  "id": 1,
  "is_pneumonia": true,
  "confidence": 70.92,
  "heatmap_url": null,
  "ai_model": "SimpleCNN",
  "created_at": "2026-08-31T16:30:00"
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | integer | 예측 결과 ID |
| `is_pneumonia` | boolean | 폐렴 예측 여부. 폐렴 확률이 50% 이상이면 `true` |
| `confidence` | number | 폐렴 예측 확률(%) |
| `heatmap_url` | string 또는 null | 히트맵 이미지 URL. 현재는 `null` |
| `ai_model` | string | 예측에 사용한 모델명 |
| `created_at` | datetime | 예측 결과 저장 일시 |

#### 오류 응답

| 상태 코드 | 상황 |
| --- | --- |
| `401` | 인증 토큰이 없거나 유효하지 않음 |
| `403` | 승인되지 않았거나 허용되지 않은 부서 사용자 |
| `404` | 진료 기록 또는 저장된 X-ray 파일을 찾을 수 없음 |
| `422` | 진료 기록에 X-ray 이미지가 없음 |

### REQ-PRED-002: 예측 결과 목록 조회

특정 진료 기록에 저장된 모든 예측 결과를 최신순으로 조회한다.

```http
GET /api/v1/medical-records/{record_id}/analyses
Authorization: Bearer <access_token>
```

#### 성공 응답: `200 OK`

```json
[
  {
    "id": 1,
    "is_pneumonia": true,
    "confidence": 70.92,
    "heatmap_url": null,
    "ai_model": "SimpleCNN",
    "created_at": "2026-08-31T16:30:00"
  }
]
```

결과가 아직 없으면 빈 배열 `[]`을 반환한다.

## 4. 데이터 설계

예측 결과는 `ai_analysis_results` 테이블에 저장한다.

| 컬럼 | 설명 |
| --- | --- |
| `record_id` | 진료 기록 ID (`medical_records.id` 외래 키) |
| `is_pneumonia` | 폐렴 예측 여부 |
| `confidence` | 폐렴 확률(소수점 둘째 자리) |
| `heatmap_url` | 히트맵 URL. 현재 빈 문자열로 저장하고 API에서는 `null`로 변환 |
| `ai_model` | 모델명 |
| `created_at` | 예측 실행·저장 시각 |

`record_id`와 `ai_model`의 복합 유니크 제약(`uq_analysis_record_model`)으로 같은 모델의 중복 저장을 방지한다.

## 5. 화면 연동

정적 화면의 [static/apis.js](../static/apis.js)는 아래 경로를 호출한다.

- AI 예측 버튼: `POST /medical-records/{record_id}/predict`
- AI 예측 결과 목록: `GET /medical-records/{record_id}/analyses`

따라서 이번 API는 기존 화면의 호출 경로를 유지한다.

## 6. 운영 및 검증

DB 제약을 적용하려면 아래 마이그레이션을 실행한다.

```bash
uv run alembic upgrade head
```

모델의 실제 Recall·Accuracy는 정답 라벨이 포함된 별도 평가 데이터셋으로 측정해야 한다. API 구현만으로는 NFR-PRED-001의 성능 목표를 보장하거나 검증할 수 없다.
