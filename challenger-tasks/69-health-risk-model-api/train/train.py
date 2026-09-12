"""
챌린저 69 - 당뇨 / 고혈압 위험도 예측 모델 학습

두 개의 이진 분류 모델을 학습한다.
  - diabetes     : 당뇨 위험
  - hypertension : 고혈압 위험

임상 위험요인(공복혈당, HbA1c, BMI, 혈압, 나이, 가족력, 흡연, 운동)을
근거로 합성 데이터를 만들고 로지스틱 회귀를 학습한다.
표준 라이브러리만 사용 -> 서빙 이미지에 ML 런타임이 필요 없다.

    python train/train.py
"""
import json
import math
import os
import random
from pathlib import Path

random.seed(2026)

FEATURES = [
    "age",
    "bmi",
    "systolic",
    "diastolic",
    "glucose",
    "hba1c",
    "family_history",
    "smoker",
    "exercise_days",
]

# 표준화 기준 (평균, 표준편차) — 추론에서도 동일하게 사용
NORM = {
    "age": (48.0, 15.0),
    "bmi": (24.5, 4.0),
    "systolic": (126.0, 16.0),
    "diastolic": (79.0, 10.0),
    "glucose": (101.0, 22.0),
    "hba1c": (5.6, 0.8),
    "family_history": (0.3, 0.46),
    "smoker": (0.25, 0.43),
    "exercise_days": (2.5, 1.8),
}

# 각 질환의 주요 위험요인 가중치 (합성 데이터 생성용)
TRUE = {
    "diabetes": {
        "weights": {
            "age": 0.35,
            "bmi": 0.75,
            "systolic": 0.15,
            "diastolic": 0.10,
            "glucose": 1.45,
            "hba1c": 1.60,
            "family_history": 0.70,
            "smoker": 0.25,
            "exercise_days": -0.40,
        },
        "bias": -1.30,
    },
    "hypertension": {
        "weights": {
            "age": 0.70,
            "bmi": 0.55,
            "systolic": 1.70,
            "diastolic": 1.30,
            "glucose": 0.20,
            "hba1c": 0.15,
            "family_history": 0.55,
            "smoker": 0.45,
            "exercise_days": -0.35,
        },
        "bias": -1.10,
    },
}


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def standardize(raw: dict) -> list:
    return [(raw[f] - NORM[f][0]) / NORM[f][1] for f in FEATURES]


def sample_person() -> dict:
    """상관관계를 반영해 한 명의 건강 지표를 생성한다."""
    age = max(20, min(85, random.gauss(48, 15)))
    bmi = max(16, min(45, random.gauss(24.5, 4)))

    # 혈압은 나이·BMI 와 함께 오른다
    systolic = max(90, min(200, random.gauss(126 + (age - 48) * 0.35 + (bmi - 24.5) * 0.9, 11)))
    diastolic = max(55, min(125, systolic * 0.62 + random.gauss(0, 5)))

    # 혈당과 HbA1c 는 서로 강하게 연동된다
    glucose = max(65, min(260, random.gauss(101 + (bmi - 24.5) * 1.6, 17)))
    hba1c = max(4.2, min(12.0, 3.6 + glucose * 0.019 + random.gauss(0, 0.32)))

    return {
        "age": round(age, 1),
        "bmi": round(bmi, 1),
        "systolic": round(systolic, 1),
        "diastolic": round(diastolic, 1),
        "glucose": round(glucose, 1),
        "hba1c": round(hba1c, 2),
        "family_history": 1.0 if random.random() < 0.3 else 0.0,
        "smoker": 1.0 if random.random() < 0.25 else 0.0,
        "exercise_days": float(random.randint(0, 7)),
    }


def make_dataset(target: str, n: int = 8000):
    spec = TRUE[target]
    rows = []
    for _ in range(n):
        raw = sample_person()
        x = standardize(raw)
        z = spec["bias"] + sum(spec["weights"][f] * xi for f, xi in zip(FEATURES, x))
        y = 1 if random.random() < sigmoid(z) else 0
        rows.append((x, y))
    return rows


def train(rows, epochs: int = 400, lr: float = 0.4, l2: float = 0.001):
    """경사하강법 + L2 정규화."""
    w = [0.0] * len(FEATURES)
    b = 0.0
    n = len(rows)

    for epoch in range(epochs):
        gw = [0.0] * len(FEATURES)
        gb = 0.0
        loss = 0.0

        for x, y in rows:
            p = sigmoid(b + sum(wi * xi for wi, xi in zip(w, x)))
            err = p - y
            for i, xi in enumerate(x):
                gw[i] += err * xi
            gb += err
            pc = min(max(p, 1e-12), 1 - 1e-12)
            loss += -(y * math.log(pc) + (1 - y) * math.log(1 - pc))

        # L2 항이 계수를 과도하게 커지지 않게 억제한다
        w = [wi - lr * (g / n + l2 * wi) for wi, g in zip(w, gw)]
        b -= lr * gb / n

        if (epoch + 1) % 200 == 0:
            print(f"    epoch {epoch + 1:>3} | loss {loss / n:.4f}")

    return w, b


def evaluate(rows, w, b, threshold: float = 0.5):
    tp = fp = tn = fn = 0
    for x, y in rows:
        p = sigmoid(b + sum(wi * xi for wi, xi in zip(w, x)))
        pred = 1 if p >= threshold else 0
        if pred and y:
            tp += 1
        elif pred and not y:
            fp += 1
        elif not pred and not y:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": round((tp + tn) / total, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def auc(rows, w, b) -> float:
    """ROC-AUC. 양성/음성 쌍에서 양성 점수가 더 높은 비율."""
    scored = [(sigmoid(b + sum(wi * xi for wi, xi in zip(w, x))), y) for x, y in rows]
    pos = [s for s, y in scored if y == 1]
    neg = [s for s, y in scored if y == 0]
    if not pos or not neg:
        return 0.0

    # 순위 기반 계산 (모든 쌍 비교 없이 O(n log n))
    scored.sort(key=lambda t: t[0])
    rank_sum = 0.0
    i = 0
    while i < len(scored):
        j = i
        while j + 1 < len(scored) and scored[j + 1][0] == scored[i][0]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        rank_sum += sum(avg_rank for _, y in scored[i : j + 1] if y == 1)
        i = j + 1

    n_pos, n_neg = len(pos), len(neg)
    return round((rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg), 4)


def main() -> None:
    out_dir = Path(os.getenv("MODEL_DIR", "models"))
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {"version": "1.0.0", "features": FEATURES, "norm": NORM, "targets": {}}

    for target in ("diabetes", "hypertension"):
        label = "당뇨" if target == "diabetes" else "고혈압"
        print(f"\n[{label}] 데이터 생성 및 학습")
        rows = make_dataset(target, 8000)
        split = int(len(rows) * 0.8)
        train_rows, test_rows = rows[:split], rows[split:]

        w, b = train(train_rows)
        metrics = evaluate(test_rows, w, b)
        metrics["auc"] = auc(test_rows, w, b)

        print(f"  평가: {json.dumps(metrics, ensure_ascii=False)}")
        top = sorted(zip(FEATURES, w), key=lambda kv: abs(kv[1]), reverse=True)[:3]
        print(f"  주요 위험요인: {[(f, round(v, 3)) for f, v in top]}")

        bundle["targets"][target] = {
            "label": label,
            "weights": dict(zip(FEATURES, [round(x, 5) for x in w])),
            "bias": round(b, 5),
            "metrics": metrics,
        }

    path = out_dir / "risk_model.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 완료: {path}")


if __name__ == "__main__":
    main()
