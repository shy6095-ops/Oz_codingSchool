from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_user
from app.core.db.databases import async_get_db
from app.models.user import User
from app.schemas.prediction import PredictionListResponse, PredictionResponse
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1/medical-records", tags=["predictions"])


def get_prediction_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PredictionService:
    return PredictionService(session)


# REQ-PRED-001 AI 폐렴 예측 실행/조회 (캐시 우선)
@router.post("/{record_id}/predictions", response_model=PredictionResponse)
async def predict(
    record_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    response: Response,
):
    result, created = await service.predict(record_id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return result


# REQ-PRED-002 AI 예측 결과 목록 조회
@router.get("/{record_id}/predictions", response_model=PredictionListResponse)
async def list_predictions(
    record_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictionService, Depends(get_prediction_service)],
):
    items = await service.list_predictions(record_id)
    return PredictionListResponse(items=items)
