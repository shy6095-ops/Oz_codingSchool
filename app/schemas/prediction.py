from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_pneumonia: bool
    confidence: float
    heatmap_url: str | None
    ai_model: str
    created_at: datetime

    @field_validator("heatmap_url", mode="before")
    @classmethod
    def empty_heatmap_is_none(cls, value: str) -> str | None:
        return value or None
