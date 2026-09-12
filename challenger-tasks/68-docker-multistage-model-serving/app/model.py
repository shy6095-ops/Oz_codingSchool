"""학습된 계수(JSON)를 읽어 추론한다. 무거운 ML 런타임이 필요 없다."""
import json
import math
import os
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/model/model.json"))


@lru_cache(maxsize=1)
def load_model() -> dict:
    """모델은 프로세스 생애주기 동안 한 번만 읽는다."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"모델 파일이 없습니다: {MODEL_PATH}. train/train.py 를 먼저 실행하세요."
        )
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def grade(probability: float) -> str:
    if probability < 0.25:
        return "낮음"
    if probability < 0.5:
        return "보통"
    if probability < 0.75:
        return "높음"
    return "매우 높음"


def predict(payload: dict) -> dict:
    """
    입력을 학습 때와 같은 기준으로 표준화한 뒤 위험도를 계산한다.
    표준화 기준이 학습/추론에서 달라지면 결과가 망가진다. (training-serving skew)
    """
    model = load_model()
    contributions = {}
    z = model["bias"]

    for feature in model["features"]:
        mean, std = model["norm"][feature]
        x = (float(payload[feature]) - mean) / std
        term = model["weights"][feature] * x
        contributions[feature] = round(term, 4)
        z += term

    probability = _sigmoid(z)
    return {
        "probability": round(probability, 4),
        "risk": grade(probability),
        "model_version": model["version"],
        # 어떤 항목이 위험도를 끌어올렸는지 보여준다 (설명 가능성)
        "contributions": dict(
            sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
        ),
    }
