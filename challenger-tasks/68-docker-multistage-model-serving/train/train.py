"""
챌린저 68 - 대사증후군 위험도 모델 학습

표준 라이브러리만 써서 로지스틱 회귀를 경사하강법으로 학습한다.
(numpy/sklearn 없이 학습 -> 서빙 이미지에 무거운 의존성이 필요 없다)

학습 결과는 model/model.json 에 계수만 저장하고,
서빙 컨테이너는 그 JSON 만 읽어 추론한다. = 모델과 서빙의 분리
"""
import json
import math
import os
import random
from pathlib import Path

random.seed(42)

FEATURES = ["bmi", "systolic", "glucose", "age", "smoker"]

# 데이터 생성에 사용할 "진짜" 관계. 학습이 이 값을 복원하는지 확인한다.
TRUE_W = {"bmi": 0.9, "systolic": 0.8, "glucose": 1.3, "age": 0.5, "smoker": 0.6}
TRUE_B = -1.1

# 표준화 기준값 (평균, 표준편차). 추론 때도 같은 값을 써야 한다.
NORM = {
    "bmi": (24.0, 4.0),
    "systolic": (125.0, 15.0),
    "glucose": (100.0, 20.0),
    "age": (45.0, 14.0),
    "smoker": (0.3, 0.46),
}


def sigmoid(z: float) -> float:
    # overflow 방지를 위해 지수 계산을 부호에 따라 나눈다.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def standardize(raw: dict) -> list:
    return [(raw[f] - NORM[f][0]) / NORM[f][1] for f in FEATURES]


def make_dataset(n: int = 6000):
    rows = []
    for _ in range(n):
        raw = {
            "bmi": random.gauss(24, 4),
            "systolic": random.gauss(125, 15),
            "glucose": random.gauss(100, 20),
            "age": random.gauss(45, 14),
            "smoker": 1.0 if random.random() < 0.3 else 0.0,
        }
        x = standardize(raw)
        z = TRUE_B + sum(TRUE_W[f] * xi for f, xi in zip(FEATURES, x))
        y = 1 if random.random() < sigmoid(z) else 0
        rows.append((x, y))
    return rows


def train(rows, epochs: int = 300, lr: float = 0.3):
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
            # 로그 손실. log(0) 방지를 위해 아주 작은 값으로 클램프한다.
            p = min(max(p, 1e-12), 1 - 1e-12)
            loss += -(y * math.log(p) + (1 - y) * math.log(1 - p))

        w = [wi - lr * g / n for wi, g in zip(w, gw)]
        b -= lr * gb / n

        if (epoch + 1) % 100 == 0:
            print(f"  epoch {epoch + 1:>3} | loss {loss / n:.4f}")

    return w, b


def evaluate(rows, w, b):
    tp = fp = tn = fn = 0
    for x, y in rows:
        pred = 1 if sigmoid(b + sum(wi * xi for wi, xi in zip(w, x))) >= 0.5 else 0
        if pred == 1 and y == 1:
            tp += 1
        elif pred == 1 and y == 0:
            fp += 1
        elif pred == 0 and y == 0:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def main() -> None:
    print("데이터 생성...")
    rows = make_dataset(6000)
    split = int(len(rows) * 0.8)
    train_rows, test_rows = rows[:split], rows[split:]

    print(f"학습 (train {len(train_rows)} / test {len(test_rows)})")
    w, b = train(train_rows)

    metrics = evaluate(test_rows, w, b)
    print("\n평가:", json.dumps(metrics, ensure_ascii=False))

    out = Path(os.getenv("MODEL_PATH", "model/model.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "features": FEATURES,
                "norm": NORM,
                "weights": dict(zip(FEATURES, [round(x, 5) for x in w])),
                "bias": round(b, 5),
                "metrics": metrics,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n저장 완료: {out}")
    print("학습된 계수:", {k: round(v, 3) for k, v in zip(FEATURES, w)})
    print("실제 계수  :", TRUE_W)


if __name__ == "__main__":
    main()
