from typing import Annotated

from fastapi import APIRouter, Depends

from app.apis.deps import get_current_prediction_user, get_prediction_service
from app.models.user import User
from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import PredictionService


router = APIRouter(prefix="/api/v1/medical-records", tags=["predictions"])


@router.post("/{record_id}/predict", response_model=PredictionResponse)
async def predict_pneumonia(
    record_id: int,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    _: Annotated[User, Depends(get_current_prediction_user)],
):
    """REQ-PRED-001: predict once per record and model, then reuse the result."""
    return await service.predict_for_record(record_id)


@router.get("/{record_id}/analyses", response_model=list[PredictionResponse])
async def get_prediction_results(
    record_id: int,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    _: Annotated[User, Depends(get_current_prediction_user)],
):
    """REQ-PRED-002: list every stored prediction result for a medical record."""
    return await service.get_result_list(record_id)
