from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.patient import Patient
from app.models.user import Gender, User
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreateRequest, PatientUpdateRequest

MEDIA_XRAY_DIR = Path(__file__).resolve().parents[2] / "media" / "xray"


class PatientService:
    def __init__(self, repository: PatientRepository):
        self.repository = repository

    async def create_patient(self, data: PatientCreateRequest) -> Patient:
        return await self.repository.create_patient(Patient(**data.model_dump()))

    async def get_patient_list(self, *, keyword: str | None, gender: Gender | None, min_age: int | None, max_age: int | None, page: int, size: int) -> tuple[int, list[Patient]]:
        if min_age is not None and max_age is not None and min_age > max_age:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="min_age는 max_age보다 클 수 없습니다.")
        return await self.repository.get_list(keyword=keyword, gender=gender, min_age=min_age, max_age=max_age, page=page, size=size)

    async def get_patient(self, patient_id: int) -> Patient:
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="환자를 찾을 수 없습니다.")
        return patient

    async def update_patient(self, patient_id: int, data: PatientUpdateRequest) -> Patient:
        patient = await self.get_patient(patient_id)
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 항목이 없습니다.")
        return await self.repository.update_patient(patient, **fields)

    async def delete_patient(self, patient_id: int) -> None:
        patient = await self.get_patient(patient_id)
        image_urls = await self.repository.get_xray_image_urls(patient)
        await self.repository.delete_patient(patient)
        for image_url in image_urls:
            (MEDIA_XRAY_DIR / Path(image_url).name).unlink(missing_ok=True)

    async def create_medical_record(self, *, patient_id: int, chart_number: str, symptoms: str, xray_image: UploadFile, uploader: User):
        patient = await self.get_patient(patient_id)
        if not xray_image.content_type or not xray_image.content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="X-Ray 이미지는 이미지 파일만 업로드할 수 있습니다.")
        filename = f"{uuid4().hex}{Path(xray_image.filename or '').suffix.lower() or '.bin'}"
        MEDIA_XRAY_DIR.mkdir(parents=True, exist_ok=True)
        image_path = MEDIA_XRAY_DIR / filename
        try:
            image_path.write_bytes(await xray_image.read())
            return await self.repository.create_medical_record(patient=patient, chart_number=chart_number, symptoms=symptoms, image_url=f"/media/xray/{filename}", uploader=uploader, shooting_datetime=datetime.now(UTC))
        except Exception:
            image_path.unlink(missing_ok=True)
            raise
        finally:
            await xray_image.close()

    async def get_medical_record_list(self, *, patient_id: int, page: int, size: int):
        await self.get_patient(patient_id)
        return await self.repository.get_medical_record_list(patient_id=patient_id, page=page, size=size)

    async def get_medical_record(self, *, patient_id: int, record_id: int):
        await self.get_patient(patient_id)
        record = await self.repository.get_medical_record(patient_id=patient_id, record_id=record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="진료기록을 찾을 수 없습니다.")
        return record
