from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_user
from app.core.db.databases import async_get_db
from app.models.user import User
from app.schemas.ai_analysis import (
    PneumoniaPredictionPageResponse,
    PneumoniaPredictionResponse,
)
from app.services.ai_analysis_service import AiAnalysisService


router = APIRouter(prefix="/api/v1/medical-records", tags=["AI pneumonia prediction"])


def get_ai_analysis_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> AiAnalysisService:
    return AiAnalysisService(session)


@router.post(
    "/{medical_record_id}/pneumonia-predictions",
    response_model=PneumoniaPredictionResponse,
)
async def create_pneumonia_prediction(
    medical_record_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[AiAnalysisService, Depends(get_ai_analysis_service)],
):
    """저장된 흉부 X-ray로 예측을 수행하고 결과를 반환한다."""
    return await service.predict_pneumonia(medical_record_id)


@router.get(
    "/{medical_record_id}/pneumonia-predictions",
    response_model=PneumoniaPredictionPageResponse,
)
async def list_pneumonia_predictions(
    medical_record_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[AiAnalysisService, Depends(get_ai_analysis_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """진료기록에 저장된 폐렴 예측 결과 목록을 반환한다."""
    return await service.list_pneumonia_predictions(medical_record_id, page, size)
