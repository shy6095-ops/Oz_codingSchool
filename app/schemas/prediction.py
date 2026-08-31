from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float
    heatmap_url: str | None
    created_at: datetime
    ai_model: str
