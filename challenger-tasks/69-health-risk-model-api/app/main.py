"""
챌린저 69 - Docker를 활용한 웹 서비스 배포 4일차
당뇨 / 고혈압 위험도 예측 서비스

  GET  /            입력 폼 (정적 페이지)
  POST /api/predict 위험도 예측
  GET  /api/model   모델 정보
  GET  /healthcheck 상태 확인
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, computed_field

from app.predictor import load_bundle, predict

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="당뇨 · 고혈압 위험도 예측 서비스",
    description="건강 지표를 입력하면 두 질환의 위험도와 생활습관 권고를 제공합니다.",
    version="1.0.0",
)


class RiskRequest(BaseModel):
    age: int = Field(..., ge=19, le=100, description="나이", examples=[52])
    height_cm: float = Field(..., ge=120, le=220, description="키 (cm)", examples=[176])
    weight_kg: float = Field(..., ge=30, le=200, description="체중 (kg)", examples=[72])
    systolic: float = Field(..., ge=70, le=250, description="수축기 혈압 (mmHg)", examples=[134])
    diastolic: float = Field(..., ge=40, le=150, description="이완기 혈압 (mmHg)", examples=[86])
    glucose: float = Field(..., ge=40, le=500, description="공복 혈당 (mg/dL)", examples=[108])
    hba1c: float = Field(..., ge=3.0, le=15.0, description="당화혈색소 (%)", examples=[5.9])
    family_history: int = Field(0, ge=0, le=1, description="직계가족 당뇨/고혈압 여부")
    smoker: int = Field(0, ge=0, le=1, description="현재 흡연 여부")
    exercise_days: int = Field(0, ge=0, le=7, description="주간 운동일수")

    @computed_field
    @property
    def bmi(self) -> float:
        """키/체중에서 BMI 를 계산한다. 사용자가 직접 입력할 필요가 없다."""
        return round(self.weight_kg / ((self.height_cm / 100) ** 2), 2)


@app.get("/healthcheck")
def healthcheck():
    bundle = load_bundle()
    return {"status": "ok", "model_version": bundle["version"]}


@app.get("/api/model")
def model_info():
    """서빙 중인 두 모델의 계수와 성능."""
    bundle = load_bundle()
    return {
        "version": bundle["version"],
        "features": bundle["features"],
        "targets": {
            k: {"label": v["label"], "metrics": v["metrics"], "weights": v["weights"]}
            for k, v in bundle["targets"].items()
        },
    }


@app.post("/api/predict")
def predict_risk(payload: RiskRequest):
    body = payload.model_dump()
    result = predict(body)
    result["input"] = {"bmi": body["bmi"], "height_cm": body["height_cm"], "weight_kg": body["weight_kg"]}
    return result


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
