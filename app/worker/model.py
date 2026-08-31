import sys
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image
from torch import nn


MODEL_NAME = "simple-cnn-v1"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "model.pth"


class SimpleCNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 32 * 32, 2),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.fc(self.conv(inputs))


@lru_cache(maxsize=1)
def get_model() -> nn.Module:
    main_module = sys.modules["__main__"]
    missing = object()
    original = getattr(main_module, "SimpleCNN", missing)
    setattr(main_module, "SimpleCNN", SimpleCNN)
    try:
        model = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    finally:
        if original is missing:
            delattr(main_module, "SimpleCNN")
        else:
            setattr(main_module, "SimpleCNN", original)
    model.eval()
    return model


def predict_xray(image_path: Path) -> tuple[bool, float]:
    with Image.open(image_path) as image:
        resized = image.convert("L").resize(
            (128, 128), resample=Image.Resampling.BILINEAR
        )
        pixels = torch.tensor(bytearray(resized.tobytes()), dtype=torch.float32)

    inputs = pixels.reshape(1, 1, 128, 128).div(255.0)
    with torch.inference_mode():
        probabilities = torch.softmax(get_model()(inputs), dim=1)[0]
    predicted_class = int(torch.argmax(probabilities).item())
    confidence = round(float(probabilities[predicted_class].item()) * 100, 2)
    return predicted_class == 1, confidence
