from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_prediction_user
from app.core.db.databases import async_get_db
from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import PredictionService
from app.worker.model import predict_xray
from app.worker.models.user import User


router = APIRouter(prefix="/api/v1/medical-records", tags=["predictions"])


def get_prediction_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PredictionService:
    return PredictionService(session, predict_xray)


@router.post("/{record_id}/predict", response_model=PredictionResponse)
async def predict_pneumonia(
    record_id: int,
    _: Annotated[User, Depends(get_current_prediction_user)],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
):
    return await service.predict(record_id)


@router.get("/{record_id}/analyses", response_model=list[PredictionResponse])
async def list_predictions(
    record_id: int,
    _: Annotated[User, Depends(get_current_prediction_user)],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
):
    return await service.list_results(record_id)
