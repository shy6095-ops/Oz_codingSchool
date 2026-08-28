from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Gender


class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, patient_id: int) -> Patient | None:
        return await self.session.get(Patient, patient_id)

    async def get_by_id_with_relations(self, patient_id: int) -> Patient | None:
        """REQ-PTNT-005: cascade 삭제 전 진료기록/X-Ray를 미리 로드해둔다 (async에서는 삭제 시점의 지연 로딩이 불가능)."""
        stmt = (
            select(Patient)
            .where(Patient.id == patient_id)
            .options(
                selectinload(Patient.medical_records).selectinload(
                    MedicalRecord.xray_images
                ),
                selectinload(Patient.medical_records).selectinload(
                    MedicalRecord.ai_analysis_results
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        *,
        search: str | None,
        gender: Gender | None,
        min_age: int | None,
        max_age: int | None,
        offset: int,
        limit: int,
    ) -> tuple[int, list[Patient]]:
        stmt = select(Patient)
        if search:
            stmt = stmt.where(Patient.name.contains(search))
        if gender:
            stmt = stmt.where(Patient.gender == gender)
        if min_age is not None:
            stmt = stmt.where(Patient.age >= min_age)
        if max_age is not None:
            stmt = stmt.where(Patient.age <= max_age)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Patient.id.desc()).offset(offset).limit(limit)
        patients = (await self.session.execute(stmt)).scalars().all()
        return total, list(patients)

    async def create(self, patient: Patient) -> Patient:
        self.session.add(patient)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def update(self, patient: Patient, **fields) -> Patient:
        for key, value in fields.items():
            setattr(patient, key, value)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def delete(self, patient: Patient) -> None:
        await self.session.delete(patient)
        await self.session.commit()
