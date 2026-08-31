import asyncio
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.patient_service import MEDIA_DIR
from app.worker.model import MODEL_NAME
from app.worker.models.ai_analysis_result import AiAnalysisResult
from app.worker.models.medical_record import MedicalRecord


class PredictionService:
    def __init__(
        self,
        session: AsyncSession,
        predictor: Callable[[Path], tuple[bool, float]],
    ) -> None:
        self.session = session
        self.predictor = predictor

    async def predict(self, record_id: int) -> AiAnalysisResult:
        record = await self._get_record(record_id)
        saved = await self.session.scalar(
            select(AiAnalysisResult)
            .where(
                AiAnalysisResult.record_id == record_id,
                AiAnalysisResult.ai_model == MODEL_NAME,
            )
            .order_by(AiAnalysisResult.id.desc())
        )
        if saved is not None:
            return saved

        if not record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="폐렴 예측에 사용할 X-Ray 이미지가 없습니다.",
            )
        image_path = MEDIA_DIR / Path(record.xray_images[0].image_url).name
        if not image_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="저장된 X-Ray 이미지 파일을 찾을 수 없습니다.",
            )

        try:
            is_pneumonia, confidence = await asyncio.to_thread(
                self.predictor, image_path
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI 예측을 수행할 수 없습니다.",
            ) from error

        result = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=is_pneumonia,
            confidence=Decimal(f"{confidence:.2f}"),
            heatmap_url=None,
            ai_model=MODEL_NAME,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def list_results(self, record_id: int) -> list[AiAnalysisResult]:
        await self._get_record(record_id)
        return list(
            (
                await self.session.scalars(
                    select(AiAnalysisResult)
                    .where(AiAnalysisResult.record_id == record_id)
                    .order_by(
                        AiAnalysisResult.created_at.desc(),
                        AiAnalysisResult.id.desc(),
                    )
                )
            ).all()
        )

    async def _get_record(self, record_id: int) -> MedicalRecord:
        record = await self.session.scalar(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == record_id)
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록을 찾을 수 없습니다.",
            )
        return record
