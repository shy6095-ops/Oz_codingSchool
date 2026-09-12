"""
챌린저 66 - Docker를 활용한 웹 서비스 배포 1일차
Docker 이미지로 빌드해서 띄우는 최소 FastAPI 서비스.
"""
import os
import platform
import socket
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Docker 1일차 - 헬스케어 체크 API",
    description="Docker build & run / Docker Compose 연습용 최소 서비스",
    version="1.0.0",
)

# 컨테이너 밖에서 주입한 환경변수. compose 에서 값을 바꿔가며 확인한다.
APP_ENV = os.getenv("APP_ENV", "local")
APP_MESSAGE = os.getenv("APP_MESSAGE", "Hello Docker!")


class BmiRequest(BaseModel):
    height_cm: float
    weight_kg: float


class BmiResponse(BaseModel):
    bmi: float
    category: str


@app.get("/")
def root():
    """컨테이너가 살아있는지, 어떤 환경으로 떴는지 한눈에 확인한다."""
    return {
        "message": APP_MESSAGE,
        "env": APP_ENV,
        # 컨테이너의 hostname 은 기본적으로 컨테이너 ID 앞 12자리다.
        # --scale 로 여러 개 띄우면 값이 서로 달라지는 걸 볼 수 있다.
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "now": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/healthcheck")
def healthcheck():
    """compose healthcheck 가 호출하는 엔드포인트."""
    return {"status": "ok"}


@app.post("/bmi", response_model=BmiResponse)
def calculate_bmi(payload: BmiRequest):
    """키(cm)와 몸무게(kg)로 BMI 와 판정 구간을 계산한다."""
    height_m = payload.height_cm / 100
    bmi = round(payload.weight_kg / (height_m**2), 2)

    if bmi < 18.5:
        category = "저체중"
    elif bmi < 23:
        category = "정상"
    elif bmi < 25:
        category = "과체중"
    elif bmi < 30:
        category = "비만 1단계"
    else:
        category = "비만 2단계 이상"

    return BmiResponse(bmi=bmi, category=category)
