from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    """REQ-PRED-001 AI 폐렴 예측 결과"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float
    heatmap_url: str | None
    ai_model: str
    created_at: datetime


class PredictionListResponse(BaseModel):
    """REQ-PRED-002 AI 예측 결과 목록 조회"""

    items: list[PredictionResponse]
