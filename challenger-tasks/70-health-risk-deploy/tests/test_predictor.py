"""추론 로직 단위 테스트 — Redis/네트워크 없이 돌아간다."""
import os
from pathlib import Path

import pytest

os.environ.setdefault(
    "MODEL_PATH", str(Path(__file__).resolve().parent.parent / "models" / "risk_model.json")
)

from app.predictor import clinical_flags, grade, predict, recommendations  # noqa: E402

HEALTHY = {
    "age": 28, "bmi": 21.0, "systolic": 110, "diastolic": 70,
    "glucose": 85, "hba1c": 5.0, "family_history": 0, "smoker": 0, "exercise_days": 5,
}
AT_RISK = {
    "age": 62, "bmi": 31.5, "systolic": 152, "diastolic": 96,
    "glucose": 141, "hba1c": 7.2, "family_history": 1, "smoker": 1, "exercise_days": 0,
}


def test_두_질환_모두_예측된다():
    result = predict(HEALTHY)
    assert set(result["results"]) == {"diabetes", "hypertension"}


def test_확률은_0과_1_사이다():
    for case in (HEALTHY, AT_RISK):
        for target in predict(case)["results"].values():
            assert 0.0 <= target["probability"] <= 1.0


def test_위험군이_건강군보다_확률이_높다():
    healthy = predict(HEALTHY)["results"]
    at_risk = predict(AT_RISK)["results"]
    for key in ("diabetes", "hypertension"):
        assert at_risk[key]["probability"] > healthy[key]["probability"]


def test_구간_경계():
    assert grade(0.10) == "낮음"
    assert grade(0.30) == "주의"
    assert grade(0.50) == "높음"
    assert grade(0.90) == "매우 높음"


def test_진단기준_초과시_danger_플래그():
    flags = clinical_flags(AT_RISK)
    assert any(f["level"] == "danger" for f in flags)
    # 혈당 141(>=126), HbA1c 7.2(>=6.5), 혈압 152/96(>=140/90) 모두 진단 기준 초과
    assert sum(1 for f in flags if f["level"] == "danger") >= 3


def test_건강군은_플래그가_없다():
    assert clinical_flags(HEALTHY) == []


def test_수정가능한_요인에만_권고한다():
    tips = " ".join(recommendations(AT_RISK, predict(AT_RISK)["results"]))
    assert "금연" in tips
    assert "운동" in tips
    # 나이는 바꿀 수 없으므로 권고에 등장하지 않아야 한다
    assert "나이를" not in tips


def test_건강군에도_권고가_하나는_있다():
    tips = recommendations(HEALTHY, predict(HEALTHY)["results"])
    assert len(tips) >= 1


def test_기여도는_내림차순이다():
    for target in predict(AT_RISK)["results"].values():
        impacts = [d["impact"] for d in target["top_drivers"]]
        assert impacts == sorted(impacts, reverse=True)
        assert all(i > 0 for i in impacts)


def test_면책조항이_포함된다():
    assert "진단이 아닙니다" in predict(HEALTHY)["disclaimer"]


@pytest.mark.parametrize("missing", ["glucose", "hba1c", "systolic"])
def test_필수값_누락시_에러(missing):
    payload = dict(HEALTHY)
    del payload[missing]
    with pytest.raises(KeyError):
        predict(payload)
