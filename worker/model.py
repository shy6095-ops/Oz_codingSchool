"""In-memory PyTorch model and image prediction helper for X-ray images."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import BinaryIO

from PIL import Image
import torch
from torch import Tensor, nn


MODEL_PATH = Path(__file__).resolve().parent / "models" / "model.pth"
IMAGE_SIZE = 128
PNEUMONIA_CLASS_INDEX = 1


class SimpleCNN(nn.Module):
    """Architecture used when the supplied model checkpoint was trained."""

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

    def forward(self, image: Tensor) -> Tensor:
        return self.fc(self.conv(image))


def _load_model() -> nn.Module:
    """Load the supplied checkpoint once, when this module is imported."""
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model file was not found: {MODEL_PATH}")

    # The supplied file was saved as ``__main__.SimpleCNN``.  Registering this
    # class lets PyTorch restore it even though inference happens in this module.
    setattr(sys.modules["__main__"], "SimpleCNN", SimpleCNN)
    model = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    if not isinstance(model, nn.Module):
        raise TypeError("The model file must contain a PyTorch nn.Module.")

    model.eval()
    return model


MODEL = _load_model()


def _to_tensor(image: Image.Image) -> Tensor:
    """Convert an uploaded image to the grayscale 128×128 model input."""
    image = image.convert("L").resize((IMAGE_SIZE, IMAGE_SIZE))
    pixels = torch.tensor(list(image.getdata()), dtype=torch.float32)
    return pixels.reshape(1, 1, IMAGE_SIZE, IMAGE_SIZE).div(255.0)


def predict(image_source: str | Path | BinaryIO) -> dict[str, bool | float]:
    """Predict pneumonia from an uploaded X-ray image.

    ``image_source`` can be the saved upload path or an open file object such as
    FastAPI's ``UploadFile.file``.  The returned confidence is a percentage.
    """
    with Image.open(image_source) as image:
        image_tensor = _to_tensor(image)

    with torch.inference_mode():
        probabilities = torch.softmax(MODEL(image_tensor), dim=1)[0]

    pneumonia_probability = probabilities[PNEUMONIA_CLASS_INDEX].item()
    return {
        "is_pneumonia": pneumonia_probability >= 0.5,
        "confidence": round(pneumonia_probability * 100, 2),
    }
