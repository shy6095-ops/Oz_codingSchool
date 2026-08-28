from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage


class MedicalRecordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id_with_xray(self, record_id: int) -> MedicalRecord | None:
        stmt = (
            select(MedicalRecord)
            .where(MedicalRecord.id == record_id)
            .options(selectinload(MedicalRecord.xray_images))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list_by_patient(self, patient_id: int) -> list[MedicalRecord]:
        stmt = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_with_xray(
        self, record: MedicalRecord, xray_image: XrayImage
    ) -> tuple[MedicalRecord, XrayImage]:
        self.session.add(record)
        await self.session.flush()

        xray_image.record_id = record.id
        self.session.add(xray_image)

        await self.session.commit()
        await self.session.refresh(record)
        await self.session.refresh(xray_image)
        return record, xray_image
