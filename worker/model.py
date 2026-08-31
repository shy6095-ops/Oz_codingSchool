# 파일/폴더 경로를 운영체제에 맞게 안전하게 다루기 위해 사용
from pathlib import Path

# 저장된 모델이 __main__.SimpleCNN을 참조하므로 호환성을 위해 사용
import __main__

# 딥러닝 모델과 텐서 계산을 위한 PyTorch
import torch

# 업로드된 이미지 파일을 열고 처리하기 위한 Pillow
from PIL import Image

# 신경망 레이어를 만들기 위한 PyTorch 모듈
from torch import nn

# 이미지 크기 변경, 흑백 변환 등의 전처리를 위한 도구
from torchvision import transforms


# ---------------------------------------------------------
# 1. 모델 구조 정의
# ---------------------------------------------------------
# model.pth 안에 저장된 SimpleCNN 모델과 같은 구조를 코드로 정의한다.
# 모델 파일을 불러올 때 구조가 다르면 가중치를 정상적으로 사용할 수 없다.
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()

        # 이미지의 특징을 추출하는 CNN 층
        self.conv = nn.Sequential(
            # 흑백 이미지 1채널을 입력받아 특징 16개를 추출한다.
            # padding=1로 이미지의 가로·세로 크기를 유지한다.
            nn.Conv2d(1, 16, kernel_size=3, padding=1),

            # 음수 값을 0으로 바꾸어 모델이 복잡한 특징을 학습하도록 돕는다.
            nn.ReLU(),

            # 이미지 크기를 절반으로 줄여 중요한 특징을 압축한다.
            # 예: 128x128 → 64x64
            nn.MaxPool2d(2),

            # 16개의 특징을 받아 더 복잡한 특징 32개를 추출한다.
            nn.Conv2d(16, 32, kernel_size=3, padding=1),

            # 두 번째 활성화 함수
            nn.ReLU(),

            # 이미지 크기를 다시 절반으로 줄인다.
            # 예: 64x64 → 32x32
            nn.MaxPool2d(2),
        )

        # 추출한 특징을 최종 분류 결과로 바꾸는 층
        self.fc = nn.Sequential(
            # (32채널, 32, 32) 형태의 데이터를 한 줄로 펼친다.
            # 32 * 32 * 32 = 32768
            nn.Flatten(),

            # 최종적으로 클래스 2개의 점수를 만든다.
            # 0번: NORMAL / 1번: PNEUMONIA
            nn.Linear(32 * 32 * 32, 2),
        )

    # 모델에 이미지 데이터가 들어왔을 때 실행되는 순서
    def forward(self, x):
        # CNN으로 이미지 특징을 추출한다.
        x = self.conv(x)

        # 추출한 특징으로 정상/폐렴 점수를 계산한다.
        return self.fc(x)


# ---------------------------------------------------------
# 2. 실행 장치와 파일 경로 설정
# ---------------------------------------------------------
# GPU를 사용할 수 있으면 GPU를 사용하고, 없으면 CPU를 사용한다.
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 현재 파일(worker/model.py)을 기준으로 model.pth의 정확한 경로를 만든다.
# 결과 경로: worker/models/model.pth
MODEL_PATH = Path(__file__).parent / "models" / "model.pth"

# 모델이 반환하는 숫자 인덱스를 사람이 읽을 수 있는 결과명으로 연결한다.
# 팀에서 확인한 라벨 순서: 0 = NORMAL, 1 = PNEUMONIA
CLASS_NAMES = ["NORMAL", "PNEUMONIA"]


# ---------------------------------------------------------
# 3. 모델을 메모리에 한 번만 올리기
# ---------------------------------------------------------
# 제공된 model.pth는 __main__.SimpleCNN이라는 이름으로 저장되어 있다.
# FastAPI 등에서 worker.model을 import하는 경우에도 모델을 읽을 수 있도록
# 현재 SimpleCNN 클래스를 __main__에 연결한다.
__main__.SimpleCNN = SimpleCNN

# model.pth 파일을 읽어 모델 객체를 메모리에 올린다.
# 이 코드는 model.py가 처음 import될 때 한 번만 실행된다.
# map_location=DEVICE는 CUDA 환경에서 학습된 모델도 CPU/Mac에서 읽게 해 준다.
# 과제에서 제공된 신뢰할 수 있는 model.pth 파일이므로 weights_only=False를 사용한다.
model = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

# 모델을 CPU 또는 GPU로 이동시킨다.
model.to(DEVICE)

# 예측 모드로 변경한다.
# 학습용 동작(Dropout, BatchNorm 등)이 있더라도 예측 시에는 고정된 방식으로 동작한다.
model.eval()


# ---------------------------------------------------------
# 4. 업로드 이미지 전처리 규칙
# ---------------------------------------------------------
# 모델이 학습된 입력 형태에 맞게 업로드 이미지를 변환한다.
preprocess = transforms.Compose([
    # X-ray 이미지를 흑백 1채널 이미지로 변환한다.
    transforms.Grayscale(num_output_channels=1),

    # 모델이 요구하는 입력 크기인 128 x 128로 맞춘다.
    transforms.Resize((128, 128)),

    # Pillow 이미지 형식을 PyTorch 텐서로 바꾼다.
    # 픽셀값도 0~255 범위에서 0~1 범위로 변환된다.
    transforms.ToTensor(),
])


# ---------------------------------------------------------
# 5. 폐렴 예측 함수
# ---------------------------------------------------------
def predict_pneumonia(image: Image.Image) -> dict:
    """
    업로드된 이미지(PIL Image)를 받아 폐렴 예측 결과를 반환한다.

    반환 예시:
    {
        "label": "PNEUMONIA",
        "class_index": 1,
        "confidence": 97.35
    }
    """

    # 어떤 이미지 형식이 들어와도 RGB 형식으로 통일한다.
    # 이후 전처리 단계에서 다시 흑백 1채널로 변환한다.
    image = image.convert("RGB")

    # 이미지 전처리 후, 모델이 요구하는 배치 차원을 추가한다.
    # 변환 전: (1, 128, 128)
    # 변환 후: (1, 1, 128, 128)
    # 첫 번째 1은 한 번에 예측할 이미지 개수(batch size)이다.
    image_tensor = preprocess(image).unsqueeze(0).to(DEVICE)

    # 예측 중에는 학습을 하지 않도록 설정한다.
    # 메모리 사용량과 연산량을 줄이고, 모델 가중치가 바뀌지 않게 한다.
    with torch.inference_mode():
        # 모델은 NORMAL과 PNEUMONIA 각각에 대한 점수(logits)를 반환한다.
        logits = model(image_tensor)

        # 두 점수를 0~1 사이의 확률값으로 변환한다.
        probabilities = torch.softmax(logits, dim=1)[0]

        # 더 높은 확률을 가진 클래스 번호를 선택한다.
        # 0이면 NORMAL, 1이면 PNEUMONIA이다.
        predicted_index = int(torch.argmax(probabilities).item())

        # 선택된 결과의 확률을 퍼센트 값으로 변환한다.
        confidence = float(probabilities[predicted_index].item()) * 100

    # API 또는 화면에서 바로 사용할 수 있는 형태로 결과를 반환한다.
    return {
        "label": CLASS_NAMES[predicted_index],
        "class_index": predicted_index,
        "confidence": round(confidence, 2),
    }