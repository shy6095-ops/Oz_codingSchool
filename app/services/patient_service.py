import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Gender
from app.models.xray_image import XrayImage
from app.schemas.patient import (
    MedicalRecordDetailResponse,
    MedicalRecordListResponse,
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)


MEDIA_DIR = Path(__file__).resolve().parents[2] / "media" / "xrays"
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _patient_response(patient: Patient) -> PatientResponse:
    return PatientResponse(
        id=patient.id,
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        phone_number=patient.phone,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


def _record_list_response(record: MedicalRecord) -> MedicalRecordListResponse:
    return MedicalRecordListResponse(
        id=record.id,
        patient_id=record.patient_id,
        chart_number=record.chart_number,
        symptoms=record.symptoms,
        created_at=record.created_at,
    )


def _record_detail_response(record: MedicalRecord) -> MedicalRecordDetailResponse:
    return MedicalRecordDetailResponse(
        **_record_list_response(record).model_dump(),
        xray_image_url=record.xray_images[0].image_url if record.xray_images else None,
    )


class PatientService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_patient(self, body: PatientCreateRequest) -> PatientResponse:
        patient = Patient(
            name=body.name,
            age=body.age,
            gender=body.gender,
            phone=body.phone_number,
        )
        self.session.add(patient)
        await self.session.commit()
        await self.session.refresh(patient)
        return _patient_response(patient)

    async def list_patients(
        self,
        name: str | None,
        gender: Gender | None,
        min_age: int | None,
        max_age: int | None,
    ) -> list[PatientResponse]:
        if min_age is not None and max_age is not None and min_age > max_age:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="최소 나이는 최대 나이보다 클 수 없습니다.",
            )

        statement = select(Patient).order_by(Patient.id.desc())
        if name:
            statement = statement.where(Patient.name.contains(name))
        if gender:
            statement = statement.where(Patient.gender == gender)
        if min_age is not None:
            statement = statement.where(Patient.age >= min_age)
        if max_age is not None:
            statement = statement.where(Patient.age <= max_age)

        patients = (await self.session.scalars(statement)).all()
        return [_patient_response(patient) for patient in patients]

    async def get_patient(self, patient_id: int) -> Patient:
        patient = await self.session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="환자를 찾을 수 없습니다.")
        return patient

    async def get_patient_response(self, patient_id: int) -> PatientResponse:
        return _patient_response(await self.get_patient(patient_id))

    async def update_patient(
        self, patient_id: int, body: PatientUpdateRequest
    ) -> PatientResponse:
        patient = await self.get_patient(patient_id)
        if body.name is not None:
            patient.name = body.name
        if body.phone_number is not None:
            patient.phone = body.phone_number
        await self.session.commit()
        await self.session.refresh(patient)
        return _patient_response(patient)

    async def delete_patient(self, patient_id: int) -> None:
        await self.get_patient(patient_id)
        image_urls = list(
            (
                await self.session.scalars(
                    select(XrayImage.image_url)
                    .join(MedicalRecord, XrayImage.record_id == MedicalRecord.id)
                    .where(MedicalRecord.patient_id == patient_id)
                )
            ).all()
        )
        record_ids = list(
            (await self.session.scalars(select(MedicalRecord.id).where(MedicalRecord.patient_id == patient_id))).all()
        )

        if record_ids:
            await self.session.execute(
                delete(AiAnalysisResult).where(AiAnalysisResult.record_id.in_(record_ids))
            )
            await self.session.execute(delete(XrayImage).where(XrayImage.record_id.in_(record_ids)))
            await self.session.execute(delete(MedicalRecord).where(MedicalRecord.id.in_(record_ids)))
        await self.session.execute(delete(Patient).where(Patient.id == patient_id))
        await self.session.commit()

        await asyncio.gather(*(self._delete_image_file(url) for url in image_urls))

    async def list_medical_records(self, patient_id: int) -> list[MedicalRecordListResponse]:
        await self.get_patient(patient_id)
        records = (
            await self.session.scalars(
                select(MedicalRecord)
                .where(MedicalRecord.patient_id == patient_id)
                .order_by(MedicalRecord.id.desc())
            )
        ).all()
        return [_record_list_response(record) for record in records]

    async def create_medical_record(
        self,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        xray_image: UploadFile | None,
    ) -> MedicalRecordDetailResponse:
        await self.get_patient(patient_id)
        image_url = await self._save_image(xray_image) if xray_image else None
        try:
            record = MedicalRecord(
                patient_id=patient_id,
                chart_number=chart_number,
                symptoms=symptoms,
            )
            self.session.add(record)
            await self.session.flush()
            if image_url:
                image = XrayImage(
                    record_id=record.id,
                    image_url=image_url,
                    shooting_datetime=datetime.now(UTC),
                )
                self.session.add(image)
            await self.session.commit()
            await self.session.refresh(record, attribute_names=["xray_images"])
            return _record_detail_response(record)
        except Exception:
            await self.session.rollback()
            if image_url:
                await self._delete_image_file(image_url)
            raise

    async def get_medical_record(self, record_id: int) -> MedicalRecordDetailResponse:
        record = await self.session.scalar(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == record_id)
        )
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="진료 기록을 찾을 수 없습니다.")
        return _record_detail_response(record)

    async def _save_image(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES or not (upload.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="X-Ray 이미지는 JPG 또는 PNG 파일만 업로드할 수 있습니다.",
            )

        content = await upload.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="빈 X-Ray 이미지는 업로드할 수 없습니다.",
            )

        filename = f"{uuid4().hex}{suffix}"
        destination = MEDIA_DIR / filename
        await asyncio.to_thread(MEDIA_DIR.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(destination.write_bytes, content)
        return f"/media/xrays/{filename}"

    async def _delete_image_file(self, image_url: str) -> None:
        path = MEDIA_DIR / Path(image_url).name
        await asyncio.to_thread(path.unlink, missing_ok=True)
