# 6일차 폐렴 예측 API 설계

## 1. 범위

REQ-PRED-001과 REQ-PRED-002에 필요한 최소 기능만 구현한다.

- 진료기록에 저장된 X-Ray 한 장으로 폐렴을 예측한다.
- 같은 진료기록과 같은 모델의 저장 결과가 있으면 재추론하지 않는다.
- 저장된 예측 결과를 진료기록 상세 화면에 표시한다.
- Heatmap은 생성하지 않고 `null`을 반환한다.
- NFR-PRED-001과 NFR-PRED-002의 측정 및 최적화는 이번 구현 범위에서 제외한다.

## 2. 모델 계약

| 항목 | 값 |
| --- | --- |
| 모델 파일 | `app/worker/models/model.pth` |
| 모델명 | `simple-cnn-v1` |
| 로딩 방식 | 모델 구조 포함 파일을 CPU 메모리에 한 번 로드 후 재사용 |
| 입력 | 흑백 1채널, `128 x 128`, `0~1` Tensor |
| 전처리 | `Grayscale -> Resize(128, 128) -> ToTensor` |
| 출력 클래스 | `0=NORMAL`, `1=PNEUMONIA` |
| 판정 | 두 logits에 softmax를 적용한 뒤 확률이 큰 클래스 선택 |
| Confidence | 선택된 클래스 확률에 100을 곱한 값, 소수점 둘째 자리까지 저장 |
| Heatmap | 생성하지 않음 (`null`) |

`model.pth`는 저장소에 포함된 파일만 로드하며, 사용자 업로드 모델 파일은 로드하지 않는다. 로드 시 CPU로 매핑하고 `eval()`과 `torch.inference_mode()`를 사용한다.

## 3. 권한

로그인 상태이며 승인된 `STAFF` 또는 `ADMIN` 사용자만 예측 및 결과 조회 API를 호출할 수 있다. 부서는 `MEDICAL`, `DEV`, `RESEARCH`를 허용하고 `PENDING` 사용자는 제외한다.

## 4. API

Base URL은 `/api/v1`이며 Bearer access token이 필요하다.

### 4.1 폐렴 예측 — REQ-PRED-001

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/v1/medical-records/{record_id}/predict` |
| 요청 본문 | 없음 |
| 성공 | `200 OK` |

처리 순서:

1. 진료기록을 조회한다.
2. `record_id`와 `simple-cnn-v1`로 저장된 결과를 조회한다.
3. 결과가 있으면 재추론 없이 해당 결과를 반환한다.
4. 결과가 없으면 진료기록에 저장된 X-Ray를 읽어 추론한다.
5. 결과를 `ai_analysis_results`에 저장하고 반환한다.

성공 응답:

```json
{
  "id": 1,
  "record_id": 10,
  "is_pneumonia": true,
  "confidence": 94.21,
  "heatmap_url": null,
  "created_at": "2026-08-31T10:00:00Z",
  "ai_model": "simple-cnn-v1"
}
```

### 4.2 예측 결과 목록 — REQ-PRED-002

| 항목 | 내용 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/v1/medical-records/{record_id}/analyses` |
| 성공 | `200 OK` |

해당 진료기록의 저장 결과를 최신 수행 일시순으로 반환한다. 저장 결과가 없으면 빈 배열을 반환한다.

```json
[
  {
    "id": 1,
    "record_id": 10,
    "is_pneumonia": true,
    "confidence": 94.21,
    "heatmap_url": null,
    "created_at": "2026-08-31T10:00:00Z",
    "ai_model": "simple-cnn-v1"
  }
]
```

## 5. 오류

| 상황 | 상태 코드 | 메시지 |
| --- | --- | --- |
| 인증 정보 없음 또는 유효하지 않음 | `401` | 기존 인증 오류 메시지 사용 |
| 승인되지 않은 사용자 | `403` | `승인된 사용자만 AI 예측 기능을 사용할 수 있습니다.` |
| 진료기록 없음 | `404` | `진료 기록을 찾을 수 없습니다.` |
| 저장된 X-Ray 없음 | `422` | `폐렴 예측에 사용할 X-Ray 이미지가 없습니다.` |
| 저장된 이미지 파일 없음 | `422` | `저장된 X-Ray 이미지 파일을 찾을 수 없습니다.` |
| 모델 로딩 또는 추론 실패 | `503` | `AI 예측을 수행할 수 없습니다.` |

## 6. 저장 및 화면 표시

기존 `ai_analysis_results` 테이블을 사용하며 선택 항목인 `heatmap_url`만 nullable로 변경한다. 별도의 모델 관리, 작업 큐, 재시도, Heatmap 생성, 성능 측정 기능은 추가하지 않는다.

진료기록 상세 화면은 다음만 수행한다.

- 진입 시 결과 목록 조회
- `AI 예측 결과보기` 클릭 시 예측 API 호출
- 응답 후 결과 목록 다시 표시
- 고유 ID, 폐렴 여부, Confidence, Heatmap URL, 수행 일시, 모델명을 표시

## 7. 검증

- 모델 파일을 CPU에서 한 번 로드하고 실제 이미지 입력을 추론할 수 있는지 확인한다.
- 저장 결과가 없는 첫 요청은 추론 결과를 저장하는지 확인한다.
- 같은 모델의 두 번째 요청은 저장 결과를 반환하고 추론을 다시 호출하지 않는지 확인한다.
- 결과 목록 필드와 정렬을 확인한다.
- 권한, 진료기록 없음, X-Ray 없음 오류를 확인한다.
- 기존 환자 및 인증 테스트가 계속 통과하는지 확인한다.
