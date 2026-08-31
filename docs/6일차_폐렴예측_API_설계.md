# AI 폐렴 예측 API 명세서

## 1. 공통 규칙

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 인증 | 로그인한 사용자만 호출 가능 |
| 허용 역할 | 사내 의료인, 개발팀, 연구자 |
| 데이터 형식 | 요청 및 응답 본문은 JSON (`application/json`) |
| 날짜 형식 | ISO 8601 UTC (`YYYY-MM-DDTHH:mm:ssZ`) |
| 응답 시간 | 모든 API는 3초 이내 응답을 목표로 함 |

> **권한**  
> 의료 데이터에는 민감 정보가 포함되므로 로그인 여부만 확인하지 않고 역할도 함께 확인해야 한다. 일반 사용자는 이 API를 호출할 수 없으며, 의료인·개발팀·연구자 역할만 허용한다.

### 공통 오류 응답 형식

```json
{
  "detail": "오류에 대한 설명"
}
```

---

## 2. 폐렴 예측 실행/조회

진료기록에 저장된 흉부 X-ray 이미지를 사용하여 폐렴 예측을 수행한다. 같은 진료기록에 이미 저장된 예측 결과가 있으면 AI 추론을 다시 실행하지 않고 저장된 결과를 반환한다.

### `POST /api/v1/medical-records/{medical_record_id}/pneumonia-predictions`

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-001 |
| 설명 | 진료기록의 X-ray 이미지를 기반으로 폐렴 여부를 예측하거나, 기존 예측 결과를 반환한다. |
| 권한 | 의료인, 개발팀, 연구자 |

> **왜 `POST`인가?**  
> 이 요청은 단순 조회가 아니라 필요할 때 AI 추론을 실행하고 결과를 DB에 저장할 수 있다. 그래서 데이터를 새로 만들 수 있는 `POST`를 사용한다. 이미 결과가 저장된 경우에는 같은 결과를 재사용하여 불필요한 모델 실행을 막는다.

#### Path Parameter

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `medical_record_id` | integer | 예 | 예측할 진료기록의 고유 ID |

#### Request Body

없음. X-ray 이미지는 진료기록 저장 시 업로드된 이미지를 사용한다.

> **이미지를 다시 업로드하지 않는 이유**  
> 요구사항은 진료기록에 저장된 X-ray를 사용하도록 정하고 있다. 따라서 프론트엔드는 파일을 다시 보내지 않고, 현재 보고 있는 진료기록 ID만 URL에 넣어 요청하면 된다.

#### 성공 응답 — `200 OK`

```json
{
  "prediction_id": 101,
  "medical_record_id": 25,
  "has_pneumonia": true,
  "confidence": 97.35,
  "heatmap_image_url": "/media/heatmaps/prediction-101.png",
  "predicted_at": "2026-08-31T06:30:00Z",
  "model_name": "SimpleCNN",
  "is_cached": false
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `prediction_id` | integer | 예측 결과의 고유 ID |
| `medical_record_id` | integer | 대상 진료기록 ID |
| `has_pneumonia` | boolean | 폐렴 예측 여부 (`true`: 폐렴, `false`: 정상) |
| `confidence` | number | 선택된 예측 결과의 신뢰도(%, 0~100) |
| `heatmap_image_url` | string \| null | Heatmap 이미지 URL. 생성하지 않는 경우 `null` |
| `predicted_at` | string | 예측 수행 또는 저장 시각 |
| `model_name` | string | 예측에 사용한 모델명 또는 모델 버전 |
| `is_cached` | boolean | 기존 저장 결과를 반환했으면 `true`, 새로 추론했으면 `false` |

> **핵심 필드 해석**  
> `has_pneumonia`는 화면에 정상/폐렴 결과를 표시하는 기준값이다. `confidence`는 모델이 선택한 결과의 확률을 백분율로 바꾼 값이며, 진단을 확정하는 의학적 판단 자체는 아니다. `heatmap_image_url`은 선택 기능이므로 아직 Heatmap을 만들지 않았다면 `null`을 반환한다.

#### 오류 응답

| 상태 코드 | 발생 상황 |
| --- | --- |
| `401 Unauthorized` | 로그인하지 않은 사용자 |
| `403 Forbidden` | 허용되지 않은 역할의 사용자 |
| `404 Not Found` | 진료기록이 없거나, 진료기록에 X-ray 이미지가 없는 경우 |
| `500 Internal Server Error` | 모델 로드 또는 예측 처리 실패 |

> **오류 처리**  
> `404`는 진료기록이 존재하지 않거나 X-ray가 아직 없는 경우에 사용한다. 모델 오류, 파일 손상 등 서버 내부 문제는 상세 기술 정보를 사용자에게 노출하지 않고 `500`으로 처리하며 서버 로그에 원인을 남긴다.

---

## 3. 폐렴 예측 결과 목록 조회

진료기록 상세 화면의 AI 예측 결과 영역에서, 해당 환자의 흉부 X-ray 및 저장된 폐렴 예측 결과 목록을 조회한다.

### `GET /api/v1/medical-records/{medical_record_id}/pneumonia-predictions`

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PRED-002 |
| 설명 | 진료기록에 연결된 폐렴 예측 결과를 최신순으로 조회한다. |
| 권한 | 의료인, 개발팀, 연구자 |

> **왜 `GET`인가?**  
> 이 API는 이미 저장된 결과를 읽기만 하며 AI 모델을 새로 실행하지 않는다. 진료기록 상세 화면에 처음 들어갈 때 또는 새로고침할 때 호출하면 된다.

#### Path Parameter

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `medical_record_id` | integer | 예 | 조회할 진료기록의 고유 ID |

#### Query Parameter

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | 아니오 | `1` | 페이지 번호. 1부터 시작 |
| `size` | integer | 아니오 | `20` | 한 페이지의 목록 수 |

> **페이지네이션**  
> 예측 이력이 많아져도 한 번에 모두 보내지 않도록 `page`와 `size`를 둔다. 프론트엔드는 `total`을 보고 다음 페이지가 있는지 판단할 수 있다. 결과가 하나뿐인 초기 단계에서도 이 구조를 유지하면 나중에 확장하기 쉽다.

#### 성공 응답 — `200 OK`

```json
{
  "medical_record_id": 25,
  "chest_xray_image_url": "/media/xrays/record-25.png",
  "items": [
    {
      "prediction_id": 101,
      "has_pneumonia": true,
      "confidence": 97.35,
      "heatmap_image_url": "/media/heatmaps/prediction-101.png",
      "predicted_at": "2026-08-31T06:30:00Z",
      "model_name": "SimpleCNN"
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `medical_record_id` | integer | 조회한 진료기록 ID |
| `chest_xray_image_url` | string \| null | 진료기록에 저장된 흉부 X-ray 이미지 URL |
| `items[].prediction_id` | integer | 예측 결과의 고유 ID |
| `items[].has_pneumonia` | boolean | 폐렴 예측 여부 |
| `items[].confidence` | number | 예측 신뢰도(%, 0~100) |
| `items[].heatmap_image_url` | string \| null | Heatmap 이미지 URL |
| `items[].predicted_at` | string | 예측 수행 일시 |
| `items[].model_name` | string | 사용한 모델명 또는 모델 버전 |
| `page` | integer | 현재 페이지 번호 |
| `size` | integer | 페이지당 결과 수 |
| `total` | integer | 전체 예측 결과 수 |

> **목록과 단건 결과의 차이**  
> `POST`의 응답은 방금 실행했거나 재사용한 결과 한 건이다. 반면 이 `GET`의 `items`는 저장된 결과들의 목록이다. 각 항목에는 요구사항에서 정한 고유 ID, 폐렴 여부, 신뢰도, Heatmap URL, 예측 일시, 사용 모델을 모두 포함한다.

#### 오류 응답

| 상태 코드 | 발생 상황 |
| --- | --- |
| `401 Unauthorized` | 로그인하지 않은 사용자 |
| `403 Forbidden` | 허용되지 않은 역할의 사용자 |
| `404 Not Found` | 진료기록이 없는 경우 |

---

## 4. 모델 평가 기준

> **평가 지표의 목적**  
> 이 표는 API 응답값이 아니라 모델 품질을 검증할 때 사용하는 기준이다. 특히 실제 폐렴 환자를 정상으로 잘못 판단하는 FN을 줄이는 것이 중요하므로, Accuracy만 보지 않고 Recall(민감도)을 함께 확인한다.

| 항목 | 기준 | 설명 |
| --- | --- | --- |
| TP | 폐렴 환자를 폐렴으로 예측 | True Positive |
| FP | 정상 환자를 폐렴으로 예측 | False Positive |
| FN | 폐렴 환자를 정상으로 예측 | False Negative. 가장 주의해야 하는 오류 |
| TN | 정상 환자를 정상으로 예측 | True Negative |
| Recall(민감도) | `0.90 ~ 0.95 이상` | 실제 폐렴 환자를 놓치지 않는 정도. `TP / (TP + FN)` |
| Accuracy(정확도) | `0.80 ~ 0.90 이상` | 전체 예측 정확도. `(TP + TN) / 전체 표본 수` |

## 5. 구현 메모

> **구현 순서 예시**  
> 1) 진료기록과 X-ray 존재 여부를 확인한다. 2) 기존 예측 결과를 조회한다. 3) 결과가 있으면 즉시 반환한다. 4) 없을 때만 `worker/model.py`의 모델로 추론한다. 5) 결과를 저장한 뒤 응답한다. 이 순서를 따르면 같은 X-ray에 대해 모델을 반복 실행하지 않는다.

- `POST` API는 먼저 해당 진료기록의 기존 예측 결과 유무를 조회한다.
- 기존 결과가 있으면 이를 즉시 반환하고, AI 모델을 다시 실행하지 않는다.
- 기존 결과가 없을 때만 `worker/model.py`의 `predict_pneumonia()`를 호출한다.
- 예측 결과는 재사용할 수 있도록 진료기록 ID, 폐렴 여부, 신뢰도, Heatmap URL, 예측 일시, 모델 정보를 저장한다.
