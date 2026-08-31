from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord


class PredictionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_record_with_images(self, record_id: int) -> MedicalRecord | None:
        result = await self.session.execute(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_result_by_model(
        self, *, record_id: int, ai_model: str
    ) -> AiAnalysisResult | None:
        result = await self.session.execute(
            select(AiAnalysisResult).where(
                AiAnalysisResult.record_id == record_id,
                AiAnalysisResult.ai_model == ai_model,
            )
        )
        return result.scalar_one_or_none()

    async def create_result(
        self,
        *,
        record_id: int,
        is_pneumonia: bool,
        confidence: Decimal,
        ai_model: str,
    ) -> AiAnalysisResult:
        result = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=is_pneumonia,
            confidence=confidence,
            # Heatmap generation is optional in REQ-PRED-001.
            heatmap_url="",
            ai_model=ai_model,
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_result_list(self, record_id: int) -> list[AiAnalysisResult]:
        result = await self.session.execute(
            select(AiAnalysisResult)
            .where(AiAnalysisResult.record_id == record_id)
            .order_by(AiAnalysisResult.created_at.desc())
        )
        return list(result.scalars())
