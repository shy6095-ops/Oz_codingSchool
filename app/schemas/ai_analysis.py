from datetime import datetime

from pydantic import BaseModel


class PneumoniaPredictionResponse(BaseModel):
    """폐렴 예측 실행 API의 단건 응답 형식."""

    prediction_id: int
    medical_record_id: int
    has_pneumonia: bool
    confidence: float
    heatmap_image_url: str | None
    predicted_at: datetime
    model_name: str
    is_cached: bool


class PneumoniaPredictionItem(BaseModel):
    """저장된 폐렴 예측 결과 목록의 한 항목."""

    prediction_id: int
    has_pneumonia: bool
    confidence: float
    heatmap_image_url: str | None
    predicted_at: datetime
    model_name: str


class PneumoniaPredictionPageResponse(BaseModel):
    """진료기록별 폐렴 예측 결과 목록 응답 형식."""

    medical_record_id: int
    chest_xray_image_url: str | None
    items: list[PneumoniaPredictionItem]
    page: int
    size: int
    total: int
