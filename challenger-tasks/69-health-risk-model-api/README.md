# 챌린저 69 — Docker를 활용한 웹 서비스 배포 4일차

**당뇨 · 고혈압 위험도 예측 서비스**를 만든다. 모델 학습부터 API, 웹 UI, 컨테이너화까지 한 서비스로 묶는 단계.

## 실행

```bash
docker compose up -d --build
open http://localhost:8000
```

- 웹 화면: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 서비스 구성

```
[브라우저] ──► GET  /               정적 입력 폼
           └─► POST /api/predict   위험도 계산 (JSON)
                      │
                      ├─ 로지스틱 회귀 2종 (당뇨 / 고혈압)
                      ├─ 임상 기준선 판정
                      └─ 생활습관 권고 생성
```

---

## 1. 모델

### 왜 표준 라이브러리로 학습했나

`train/train.py` 는 **numpy·sklearn 없이** 경사하강법으로 로지스틱 회귀를 학습한다.

- 학습 산출물이 `models/risk_model.json` (계수 + 표준화 기준 + 성능)뿐이다
- 서빙 컨테이너에 ML 런타임이 필요 없어 이미지가 작다
- 계수를 그대로 읽을 수 있어 **"왜 이 결과인지" 설명이 가능**하다

### 입력 변수 9개

| 변수 | 설명 |
| --- | --- |
| `age` | 나이 |
| `bmi` | 키·체중에서 자동 계산 |
| `systolic` / `diastolic` | 수축기 / 이완기 혈압 |
| `glucose` | 공복 혈당 |
| `hba1c` | 당화혈색소 |
| `family_history` | 직계가족 병력 |
| `smoker` | 현재 흡연 |
| `exercise_days` | 주간 운동일수 |

합성 데이터는 변수 간 상관관계를 반영해 생성한다. 혈압은 나이·BMI 와 함께 오르고, HbA1c 는 공복혈당에 연동된다. 독립적으로 뽑으면 현실에 없는 조합(혈당 250인데 HbA1c 4.5)이 나와 모델이 엉뚱한 관계를 학습한다.

### 학습 결과

| 모델 | accuracy | precision | recall | F1 | **AUC** |
| --- | --- | --- | --- | --- | --- |
| 당뇨 | 0.856 | 0.790 | 0.695 | 0.740 | **0.908** |
| 고혈압 | 0.845 | 0.811 | 0.743 | 0.775 | **0.928** |

학습된 계수가 임상 지식과 일치한다 — 우연이 아니라 데이터에 심어둔 관계를 복원한 것이다.

| 모델 | 상위 위험요인 (계수) |
| --- | --- |
| 당뇨 | HbA1c (1.573) · 공복혈당 (1.325) · BMI (0.714) |
| 고혈압 | 수축기 혈압 (1.540) · 이완기 혈압 (1.467) · 나이 (0.693) |

과적합을 막기 위해 L2 정규화(`l2=0.001`)를 넣었고, AUC 는 순위 기반으로 계산해 모든 쌍을 비교하지 않는다.

---

## 2. API

### BMI 를 서버에서 계산하는 이유

```python
@computed_field
@property
def bmi(self) -> float:
    return round(self.weight_kg / ((self.height_cm / 100) ** 2), 2)
```

사용자는 키·체중만 입력한다. BMI 를 직접 받으면 키·체중과 어긋난 값이 들어올 수 있다. 파생값은 **한 곳에서만** 계산해야 한다.

### 모델 확률과 임상 기준을 함께 본다

모델 확률만 보여주면 위험하다. 확률이 낮게 나와도 **진단 기준을 넘는 값**이 있으면 반드시 알려야 한다.

```python
if v["glucose"] >= 126:   # 당뇨 진단 기준
if v["hba1c"] >= 6.5:     # 당뇨 진단 기준
if v["systolic"] >= 140 or v["diastolic"] >= 90:   # 고혈압 기준
```

`clinical_flags()` 가 모델과 **독립적으로** 기준선을 검사한다. 모델은 참고 지표, 기준선은 사실 확인이라는 역할 분리다.

### 권고는 수정 가능한 요인에만

나이·가족력처럼 바꿀 수 없는 요인에는 권고하지 않는다. 체중, 운동, 흡연, 나트륨, 정제 탄수화물처럼 **행동으로 바꿀 수 있는 것**만 제시한다. (가족력은 "정기검진" 권고로만 연결)

### 요청 / 응답

```bash
curl -X POST localhost:8000/api/predict -H 'Content-Type: application/json' -d '{
  "age": 52, "height_cm": 176, "weight_kg": 82,
  "systolic": 138, "diastolic": 88,
  "glucose": 112, "hba1c": 6.1,
  "family_history": 1, "smoker": 0, "exercise_days": 1
}'
```

```json
{
  "model_version": "1.0.0",
  "results": {
    "diabetes": {
      "label": "당뇨", "percent": 91.4, "risk": "매우 높음",
      "top_drivers": [
        {"factor": "가족력", "impact": 1.056},
        {"factor": "HbA1c", "impact": 0.9829},
        {"factor": "공복 혈당", "impact": 0.6625}
      ],
      "model_auc": 0.9084
    },
    "hypertension": { "percent": 94.6, "risk": "매우 높음", "...": "..." }
  },
  "clinical_flags": [
    {"level": "warn", "text": "공복혈당 112 mg/dL — 공복혈당장애(100~125)"},
    {"level": "warn", "text": "HbA1c 6.1% — 당뇨 전단계(5.7~6.4)"},
    {"level": "warn", "text": "혈압 138/88 mmHg — 주의 혈압(130/80 이상)"},
    {"level": "warn", "text": "BMI 26.4 — 비만(25 이상)"}
  ],
  "recommendations": ["..."],
  "disclaimer": "본 결과는 통계 모델의 참고 지표이며 의학적 진단이 아닙니다."
}
```

| 엔드포인트 | 설명 |
| --- | --- |
| `GET /` | 입력 폼 |
| `POST /api/predict` | 위험도 예측 |
| `GET /api/model` | 모델 버전·계수·성능 |
| `GET /healthcheck` | 컨테이너 상태 |

---

## 3. 웹 UI

- 입력 중 **BMI 실시간 표시** — 키·체중을 고치면 즉시 갱신
- 위험도 카드: 확률 + 구간(낮음/주의/높음/매우 높음) + 게이지 바 + 상위 위험요인 + 모델 AUC
- 위험 구간에 따라 카드 색이 바뀐다 (초록 → 주황 → 빨강)
- 검진 기준 확인(`warn`/`danger`)과 생활습관 권고를 별도 카드로 분리
- 820px 이하에서 1열로 스택, 460px 이하에서 입력도 1열

### 잡은 버그

결과 영역에 `hidden` 을 걸었는데도 계산 전부터 보였다.

```css
.result { display: flex; ... }   /* ← UA 의 [hidden]{display:none} 을 덮어씀 */
```

`display` 를 지정한 요소에는 `hidden` 속성이 무력화된다. 명시적으로 되살려야 한다.

```css
[hidden] { display: none !important; }
```

---

## 4. 컨테이너화

멀티스테이지 빌드로 **빌드 시점에 모델을 학습**해 이미지에 굽는다.

```dockerfile
FROM python:3.13-slim AS builder
RUN MODEL_DIR=/install/models python train/train.py

FROM python:3.13-slim AS runtime
COPY --from=builder /install/models /app/models    # 학습된 JSON 만
USER appuser                                        # 비root 실행
```

학습 스크립트와 빌드 캐시는 최종 이미지에 남지 않는다. 컨테이너를 몇 개 띄워도 **같은 모델**이 서빙된다.

---

## 파일 구성

```
69-health-risk-model-api/
├── train/train.py           # 당뇨·고혈압 2종 모델 학습 (표준 라이브러리)
├── models/risk_model.json   # 계수 + 표준화 기준 + 성능
├── app/
│   ├── predictor.py         # 추론 + 임상 기준 판정 + 권고 생성
│   └── main.py              # FastAPI 라우팅, BMI computed_field
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── Dockerfile               # 멀티스테이지 + 비root
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
└── README.md
```

## 확인 포인트

- [x] 두 모델 학습 완료, AUC 0.908 / 0.928
- [x] 학습된 계수가 임상 위험요인과 일치
- [x] BMI 를 서버에서 파생 계산
- [x] 모델 확률과 임상 기준선을 분리해 함께 제공
- [x] 위험요인 기여도(`top_drivers`)로 결과 설명
- [x] 웹 UI 에서 입력 → 계산 → 결과 표시 동작 확인
- [x] 멀티스테이지 빌드, 비root 실행
