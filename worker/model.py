from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "resnet18_pneumonia.pth"
MODEL_NAME = "resnet18-pneumonia-v1"

# 학습 시(노트북 [Mission0-4]_흉부Xray_폐렴분류_ResNet18적용.ipynb)와 동일한 전처리를 사용해야
# 정확도가 재현된다.
IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]  # 학습 시 라벨: 0=NORMAL, 1=PNEUMONIA

_preprocess = transforms.Compose(
    [
        transforms.Grayscale(num_output_channels=3),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
)


def _build_model() -> nn.Module:
    # 학습된 가중치를 그대로 덮어씌울 것이므로 ImageNet 사전학습 가중치는 필요 없다.
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(CLASS_NAMES))
    state_dict = torch.load(MODEL_PATH, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    return model


# 모듈이 처음 import될 때 모델을 한 번만 메모리에 올려둔다.
_model = _build_model()


def predict_pneumonia(image: Image.Image) -> dict:
    """흉부 X-ray 이미지를 받아 폐렴 여부와 확신도(%)를 반환한다."""
    tensor = _preprocess(image.convert("L")).unsqueeze(0)
    with torch.no_grad():
        logits = _model(tensor)
        probabilities = torch.softmax(logits, dim=1)[0]

    predicted_index = int(probabilities.argmax())
    return {
        "is_pneumonia": predicted_index == 1,
        # 기존 pneumonia-predictions endpoint와의 응답 호환성도 유지한다.
        "class_index": predicted_index,
        "label": CLASS_NAMES[predicted_index],
        "confidence": round(probabilities[predicted_index].item() * 100, 2),
        "ai_model": MODEL_NAME,
    }


if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        result = predict_pneumonia(Image.open(path))
        print(path, "->", result)
