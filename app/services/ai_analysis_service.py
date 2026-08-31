import asyncio
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord
from app.schemas.ai_analysis import (
    PneumoniaPredictionItem,
    PneumoniaPredictionPageResponse,
    PneumoniaPredictionResponse,
)
from worker.model import predict_pneumonia


MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
MODEL_NAME = "SimpleCNN"


def _to_image_path(image_url: str) -> Path:
    """DB에 저장된 /media/... URL을 실제 프로젝트 파일 경로로 바꾼다."""
    try:
        relative_path = Path(image_url).relative_to("/media")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="저장된 X-Ray 이미지 경로가 올바르지 않습니다.",
        )
    return MEDIA_ROOT / relative_path


def _run_prediction(image_path: Path) -> dict:
    """이미지를 열고 worker/model.py의 메모리 내 모델로 예측한다."""
    with Image.open(image_path) as image:
        return predict_pneumonia(image)


def _prediction_response(
    result: AiAnalysisResult, *, is_cached: bool
) -> PneumoniaPredictionResponse:
    """DB 모델의 필드명을 API 명세의 응답 필드명으로 변환한다."""
    return PneumoniaPredictionResponse(
        prediction_id=result.id,
        medical_record_id=result.record_id,
        has_pneumonia=result.is_pneumonia,
        confidence=float(result.confidence),
        heatmap_image_url=result.heatmap_url or None,
        predicted_at=result.created_at,
        model_name=result.ai_model,
        is_cached=is_cached,
    )


class AiAnalysisService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def predict_pneumonia(
        self, medical_record_id: int
    ) -> PneumoniaPredictionResponse:
        """기존 결과는 재사용하고, 없을 때만 X-ray 예측을 실행한다."""
        record = await self.session.scalar(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == medical_record_id)
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록을 찾을 수 없습니다.",
            )
        if not record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록에 저장된 X-Ray 이미지가 없습니다.",
            )

        saved_result = await self.session.scalar(
            select(AiAnalysisResult)
            .where(AiAnalysisResult.record_id == medical_record_id)
            .order_by(AiAnalysisResult.created_at.desc())
        )
        if saved_result is not None:
            return _prediction_response(saved_result, is_cached=True)

        image_path = _to_image_path(record.xray_images[0].image_url)
        if not image_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="저장된 X-Ray 이미지 파일을 찾을 수 없습니다.",
            )

        try:
            # PyTorch 추론은 동기 작업이므로 이벤트 루프를 막지 않도록 별도 스레드에서 수행한다.
            prediction = await asyncio.to_thread(_run_prediction, image_path)
        except (OSError, UnidentifiedImageError) as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="X-Ray 이미지를 분석할 수 없습니다.",
            ) from error
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="폐렴 예측 중 오류가 발생했습니다.",
            ) from error

        result = AiAnalysisResult(
            record_id=medical_record_id,
            is_pneumonia=prediction["class_index"] == 1,
            confidence=prediction["confidence"],
            # Heatmap은 요구사항의 선택 기능이며, 아직 생성하지 않으므로 빈 값으로 저장한다.
            heatmap_url="",
            ai_model=MODEL_NAME,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return _prediction_response(result, is_cached=False)

    async def list_pneumonia_predictions(
        self, medical_record_id: int, page: int, size: int
    ) -> PneumoniaPredictionPageResponse:
        """진료기록의 X-ray URL 및 저장된 예측 결과를 최신순으로 반환한다."""
        record = await self.session.scalar(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == medical_record_id)
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록을 찾을 수 없습니다.",
            )

        total = await self.session.scalar(
            select(func.count())
            .select_from(AiAnalysisResult)
            .where(AiAnalysisResult.record_id == medical_record_id)
        )
        results = (
            await self.session.scalars(
                select(AiAnalysisResult)
                .where(AiAnalysisResult.record_id == medical_record_id)
                .order_by(AiAnalysisResult.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        ).all()

        return PneumoniaPredictionPageResponse(
            medical_record_id=medical_record_id,
            chest_xray_image_url=(
                record.xray_images[0].image_url if record.xray_images else None
            ),
            items=[
                PneumoniaPredictionItem(
                    prediction_id=result.id,
                    has_pneumonia=result.is_pneumonia,
                    confidence=float(result.confidence),
                    heatmap_image_url=result.heatmap_url or None,
                    predicted_at=result.created_at,
                    model_name=result.ai_model,
                )
                for result in results
            ],
            page=page,
            size=size,
            total=total or 0,
        )
