from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Gender, User
from app.models.xray_image import XrayImage


class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, patient_id: int) -> Patient | None:
        return await self.session.get(Patient, patient_id)

    async def get_list(self, *, keyword: str | None, gender: Gender | None, min_age: int | None, max_age: int | None, page: int, size: int) -> tuple[int, list[Patient]]:
        stmt = select(Patient)
        if keyword:
            stmt = stmt.where(Patient.name.contains(keyword))
        if gender:
            stmt = stmt.where(Patient.gender == gender)
        if min_age is not None:
            stmt = stmt.where(Patient.age >= min_age)
        if max_age is not None:
            stmt = stmt.where(Patient.age <= max_age)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        patients = (await self.session.execute(stmt.order_by(Patient.id.desc()).offset((page - 1) * size).limit(size))).scalars().all()
        return total, list(patients)

    async def create_patient(self, patient: Patient) -> Patient:
        self.session.add(patient)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def update_patient(self, patient: Patient, **fields) -> Patient:
        for key, value in fields.items():
            setattr(patient, key, value)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def get_xray_image_urls(self, patient: Patient) -> list[str]:
        result = await self.session.execute(select(XrayImage.image_url).join(MedicalRecord).where(MedicalRecord.patient_id == patient.id))
        return list(result.scalars())

    async def delete_patient(self, patient: Patient) -> None:
        await self.session.delete(patient)
        await self.session.commit()

    async def create_medical_record(self, *, patient: Patient, chart_number: str, symptoms: str, image_url: str, uploader: User, shooting_datetime: datetime) -> tuple[MedicalRecord, XrayImage]:
        record = MedicalRecord(patient=patient, chart_number=chart_number, symptoms=symptoms)
        self.session.add(record)
        await self.session.flush()
        image = XrayImage(medical_record=record, uploader=uploader, image_url=image_url, shooting_datetime=shooting_datetime)
        self.session.add(image)
        await self.session.commit()
        await self.session.refresh(record)
        return record, image

    async def get_medical_record_list(self, *, patient_id: int, page: int, size: int) -> tuple[int, list[MedicalRecord]]:
        stmt = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        records = (await self.session.execute(stmt.order_by(MedicalRecord.id.desc()).offset((page - 1) * size).limit(size))).scalars().all()
        return total, list(records)

    async def get_medical_record(self, *, patient_id: int, record_id: int) -> MedicalRecord | None:
        result = await self.session.execute(select(MedicalRecord).options(selectinload(MedicalRecord.xray_images)).where(MedicalRecord.id == record_id, MedicalRecord.patient_id == patient_id))
        return result.scalar_one_or_none()
