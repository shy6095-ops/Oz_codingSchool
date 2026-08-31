from pathlib import Path

from PIL import Image

from app.worker.model import get_model, predict_xray


def test_model_is_cached_and_predicts_a_percentage(tmp_path: Path) -> None:
    image_path = tmp_path / "xray.png"
    Image.new("L", (128, 128), color=128).save(image_path)

    assert get_model() is get_model()

    is_pneumonia, confidence = predict_xray(image_path)

    assert isinstance(is_pneumonia, bool)
    assert 0.0 <= confidence <= 100.0
    assert confidence == round(confidence, 2)
