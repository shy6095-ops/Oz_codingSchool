from datetime import datetime

from fastapi import HTTPException, UploadFile, status

from app.core.storage import save_xray_image
from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository

SYMPTOMS_PREVIEW_LIMIT = 100


def truncate_symptoms(symptoms: str) -> str:
    if len(symptoms) > SYMPTOMS_PREVIEW_LIMIT:
        return symptoms[:SYMPTOMS_PREVIEW_LIMIT] + "..."
    return symptoms


class MedicalRecordService:
    def __init__(
        self,
        repository: MedicalRecordRepository,
        patient_repository: PatientRepository,
    ):
        self.repository = repository
        self.patient_repository = patient_repository

    # REQ-MDR-001 진료기록 등록 (X-Ray 이미지 업로드 포함)
    async def create(
        self,
        *,
        patient_id: int,
        chart_number: str,
        symptoms: str,
        shooting_datetime: datetime,
        xray_file: UploadFile,
        uploader_id: int | None,
    ) -> tuple[MedicalRecord, XrayImage]:
        patient = await self.patient_repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 환자를 찾을 수 없습니다.",
            )

        image_url = await save_xray_image(xray_file)
        record = MedicalRecord(
            patient_id=patient_id, chart_number=chart_number, symptoms=symptoms
        )
        xray_image = XrayImage(
            image_url=image_url,
            shooting_datetime=shooting_datetime,
            uploader_id=uploader_id,
        )
        return await self.repository.create_with_xray(record, xray_image)

    # REQ-MDR-002 진료기록 목록 조회
    async def get_list_by_patient(self, patient_id: int) -> list[MedicalRecord]:
        patient = await self.patient_repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 환자를 찾을 수 없습니다.",
            )
        return await self.repository.get_list_by_patient(patient_id)

    # REQ-MDR-003 진료기록 상세 조회
    async def get_by_id(self, record_id: int) -> MedicalRecord:
        record = await self.repository.get_by_id_with_xray(record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 진료기록을 찾을 수 없습니다.",
            )
        return record
