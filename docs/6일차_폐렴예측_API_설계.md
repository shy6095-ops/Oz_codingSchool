# 6일차 - 폐렴 예측 API 설계

## 1. 개요
`6일차 - AI 폐렴 예측 사용자 요구사항 정의서`(`REQ-PRED-001~002`, `NFR-PRED-001~002`)를 기반으로 설계한 API입니다. 5일차에서 만든 `MedicalRecord`/`XrayImage`에 이어, 진료기록에 대한 AI 폐렴 예측 결과를 저장·조회합니다. 예측 로직은 `worker/model.py`의 `predict_pneumonia()`(ResNet18 전이학습 모델)를 그대로 사용합니다.

- Base URL: `/api/v1`
- 인증: 로그인 필요 (`Authorization: Bearer <access_token>`). 의료인/개발팀/연구자 구분 없이 로그인한 유저면 누구나 접근 가능 (부서 제한 없음 — 3개 부서가 곧 전체 유저이므로 사실상 로그인 여부만 확인).
- 저장소: `ai_analysis_results` 테이블 (기존 `AiAnalysisResult` 모델 그대로 사용)

### 공통 에러
| 상태 코드 | 의미 |
|---|---|
| 401 | 인증 실패 |
| 404 | 진료기록 없음 |
| 422 | 해당 진료기록에 X-Ray 이미지가 없어 예측 불가 |

---

## 2. 엔드포인트 명세

### 2.1 AI 폐렴 예측 실행/조회
- **요구사항 ID**: REQ-PRED-001
- **Method / Path**: `POST /api/v1/medical-records/{record_id}/predictions`
- **설명**: 진료기록 상세 페이지의 "AI 예측 결과보기" 버튼에 대응. 해당 진료기록에 **같은 모델(`ai_model`)로 이미 저장된 예측 결과가 있으면 그 값을 그대로 반환**하고(재추론 없음), 없으면 진료기록에 연결된 X-Ray 이미지로 새로 추론해서 저장 후 반환한다.
- **캐시 판단 기준**: `(record_id, ai_model)` 조합으로 기존 `ai_analysis_results` row 존재 여부 확인.

**Request Body**: 없음

**Response `200 OK`** (캐시된 결과) 또는 **`201 Created`** (새로 추론)
```json
{
  "id": 1,
  "record_id": 10,
  "is_pneumonia": true,
  "confidence": 99.87,
  "heatmap_url": null,
  "ai_model": "resnet18-pneumonia-v1",
  "created_at": "2026-08-31T10:00:00"
}
```

**에러**
- `404` 해당 진료기록 없음
- `422` 진료기록에 연결된 X-Ray 이미지가 없음

---

### 2.2 AI 예측 결과 목록 조회
- **요구사항 ID**: REQ-PRED-002
- **Method / Path**: `GET /api/v1/medical-records/{record_id}/predictions`
- **설명**: 진료기록 상세 페이지의 "AI 예측 결과" 섹션에서, 해당 진료기록에 대해 지금까지 수행된 모든 예측 결과를 목록으로 조회한다 (모델을 바꿔가며 여러 번 예측했을 수 있으므로 여러 건일 수 있음).

**Response `200 OK`**
```json
{
  "items": [
    {
      "id": 1,
      "record_id": 10,
      "is_pneumonia": true,
      "confidence": 99.87,
      "heatmap_url": null,
      "ai_model": "resnet18-pneumonia-v1",
      "created_at": "2026-08-31T10:00:00"
    }
  ]
}
```

**에러**
- `404` 해당 진료기록 없음

---

## 3. 비기능 요구사항(NFR) 대응
| ID | 내용 | 반영 방식 |
|---|---|---|
| NFR-PRED-001 | Recall ≥ 0.90, Accuracy ≥ 0.80 (FN이 가장 위험하므로 Recall 우선) | `worker/model.py`의 ResNet18 모델은 재학습 검증 결과 PNEUMONIA 클래스 **Recall 0.9936**, **Accuracy 0.9895**로 기준을 충분히 상회함 (학습 로그 기준) |
| NFR-PRED-002 | 3초 이내 응답 | 비동기 핸들러 + 캐시 우선 반환(동일 모델 재추론 방지)으로 대부분의 요청은 DB 조회만으로 응답 |

---

## 4. 구현 메모
- **heatmap_url**: 요구사항상 "선택사항"이지만, 현재 `ai_analysis_results.heatmap_url` 컬럼이 `NOT NULL`이라 마이그레이션으로 nullable 처리가 필요하다. 초기 구현에서는 Grad-CAM 히트맵 생성을 포함하지 않고 `null`로 저장한다 (추후 별도 과제로 확장 가능).
- **X-Ray 이미지 선택**: 한 진료기록에 여러 X-Ray가 연결될 수 있는 구조(`XrayImage.record_id`가 1:N)이므로, 예측 시에는 해당 진료기록에 연결된 **가장 최근 X-Ray 이미지**를 사용한다.
