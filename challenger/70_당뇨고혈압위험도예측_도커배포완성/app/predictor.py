"""위험도 계산 + 임상 기준 판정 + 생활습관 권고."""
import json
import math
import os
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/risk_model.json"))

FEATURE_LABELS = {
    "age": "나이",
    "bmi": "BMI",
    "systolic": "수축기 혈압",
    "diastolic": "이완기 혈압",
    "glucose": "공복 혈당",
    "hba1c": "HbA1c",
    "family_history": "가족력",
    "smoker": "흡연",
    "exercise_days": "주간 운동일수",
}


@lru_cache(maxsize=1)
def load_bundle() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"모델이 없습니다: {MODEL_PATH}. train/train.py 를 먼저 실행하세요."
        )
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def grade(p: float) -> str:
    if p < 0.20:
        return "낮음"
    if p < 0.40:
        return "주의"
    if p < 0.65:
        return "높음"
    return "매우 높음"


def clinical_flags(v: dict) -> list:
    """
    모델과 별개로 임상 기준선을 직접 확인한다.
    모델 확률이 낮게 나와도 기준을 넘는 값이 있으면 반드시 알려야 한다.
    (대한당뇨병학회 / 대한고혈압학회 기준 참고)
    """
    flags = []

    if v["glucose"] >= 126:
        flags.append({"level": "danger", "text": f"공복혈당 {v['glucose']:.0f} mg/dL — 당뇨 진단 기준(126 이상)"})
    elif v["glucose"] >= 100:
        flags.append({"level": "warn", "text": f"공복혈당 {v['glucose']:.0f} mg/dL — 공복혈당장애(100~125)"})

    if v["hba1c"] >= 6.5:
        flags.append({"level": "danger", "text": f"HbA1c {v['hba1c']:.1f}% — 당뇨 진단 기준(6.5 이상)"})
    elif v["hba1c"] >= 5.7:
        flags.append({"level": "warn", "text": f"HbA1c {v['hba1c']:.1f}% — 당뇨 전단계(5.7~6.4)"})

    if v["systolic"] >= 140 or v["diastolic"] >= 90:
        flags.append({
            "level": "danger",
            "text": f"혈압 {v['systolic']:.0f}/{v['diastolic']:.0f} mmHg — 고혈압 기준(140/90 이상)",
        })
    elif v["systolic"] >= 130 or v["diastolic"] >= 80:
        flags.append({
            "level": "warn",
            "text": f"혈압 {v['systolic']:.0f}/{v['diastolic']:.0f} mmHg — 주의 혈압(130/80 이상)",
        })

    if v["bmi"] >= 25:
        flags.append({"level": "warn", "text": f"BMI {v['bmi']:.1f} — 비만(25 이상)"})
    elif v["bmi"] < 18.5:
        flags.append({"level": "warn", "text": f"BMI {v['bmi']:.1f} — 저체중(18.5 미만)"})

    return flags


def recommendations(v: dict, results: dict) -> list:
    """수정 가능한 위험요인에 대해서만 권고한다."""
    tips = []

    if v["bmi"] >= 25:
        target = round(22.5 * ((v.get("height_cm", 170) / 100) ** 2), 1) if v.get("height_cm") else None
        tips.append(
            f"체중 감량이 두 질환 위험을 동시에 낮춥니다. 현재 체중의 5~7% 감량이 1차 목표입니다."
            + (f" (목표 체중 약 {target}kg)" if target else "")
        )
    if v["exercise_days"] < 3:
        tips.append("중강도 유산소 운동을 주 150분(주 5일 30분) 이상으로 늘려보세요.")
    if v["smoker"] == 1:
        tips.append("금연은 혈압과 혈관 건강에 가장 큰 단일 효과를 냅니다.")
    if v["systolic"] >= 130 or v["diastolic"] >= 80:
        tips.append("나트륨을 하루 2,000mg 이하로 줄이고 가정혈압을 아침·저녁 측정해 기록하세요.")
    if v["glucose"] >= 100 or v["hba1c"] >= 5.7:
        tips.append("정제 탄수화물과 당류 섭취를 줄이고, 3~6개월 뒤 공복혈당·HbA1c 를 재검사하세요.")
    if v["family_history"] == 1:
        tips.append("가족력이 있으면 증상이 없어도 연 1회 정기검진을 권합니다.")

    if any(r["probability"] >= 0.65 for r in results.values()):
        tips.insert(0, "위험도가 높게 산출되었습니다. 가까운 의료기관에서 진료를 받아보세요.")

    if not tips:
        tips.append("현재 지표는 양호합니다. 연 1회 건강검진으로 추이를 관찰하세요.")

    return tips


def predict(payload: dict) -> dict:
    bundle = load_bundle()
    features = bundle["features"]
    norm = bundle["norm"]

    # 표준화된 입력값 (학습 때와 동일한 기준)
    x = {f: (float(payload[f]) - norm[f][0]) / norm[f][1] for f in features}

    results = {}
    for target, spec in bundle["targets"].items():
        z = spec["bias"]
        contributions = {}
        for f in features:
            term = spec["weights"][f] * x[f]
            contributions[FEATURE_LABELS[f]] = round(term, 4)
            z += term

        p = _sigmoid(z)
        # 위험도를 끌어올린 요인만 상위 3개 추려 보여준다
        drivers = [
            {"factor": k, "impact": v}
            for k, v in sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
            if v > 0
        ][:3]

        results[target] = {
            "label": spec["label"],
            "probability": round(p, 4),
            "percent": round(p * 100, 1),
            "risk": grade(p),
            "top_drivers": drivers,
            "model_auc": spec["metrics"]["auc"],
        }

    return {
        "model_version": bundle["version"],
        "results": results,
        "clinical_flags": clinical_flags(payload),
        "recommendations": recommendations(payload, results),
        "disclaimer": "본 결과는 통계 모델의 참고 지표이며 의학적 진단이 아닙니다.",
    }
