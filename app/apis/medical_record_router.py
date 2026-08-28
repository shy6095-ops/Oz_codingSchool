from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_medical_staff, get_current_user
from app.core.db.databases import async_get_db
from app.models.user import User
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
    MedicalRecordListResponse,
    MedicalRecordResponse,
)
from app.services.medical_record_service import MedicalRecordService, truncate_symptoms

router = APIRouter(prefix="/api/v1", tags=["medical-records"])


def get_medical_record_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> MedicalRecordService:
    return MedicalRecordService(
        MedicalRecordRepository(session), PatientRepository(session)
    )


# REQ-MDR-001 진료기록 등록 (X-Ray 이미지 업로드 포함, multipart/form-data, 사내 의료인 전용)
@router.post(
    "/patients/{patient_id}/medical-records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_medical_record(
    patient_id: int,
    service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    current_user: Annotated[User, Depends(get_current_medical_staff)],
    chart_number: Annotated[str, Form()],
    symptoms: Annotated[str, Form()],
    shooting_datetime: Annotated[datetime, Form()],
    xray_image: Annotated[UploadFile, File()],
):
    record, xray = await service.create(
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        shooting_datetime=shooting_datetime,
        xray_file=xray_image,
        uploader_id=current_user.id,
    )
    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        chart_number=record.chart_number,
        symptoms=record.symptoms,
        xray_image_url=xray.image_url,
        created_at=record.created_at,
    )


# REQ-MDR-002 진료기록 목록 조회
@router.get(
    "/patients/{patient_id}/medical-records", response_model=MedicalRecordListResponse
)
async def get_medical_record_list(
    patient_id: int,
    service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    records = await service.get_list_by_patient(patient_id)
    items = [
        MedicalRecordListItem(
            id=record.id,
            chart_number=record.chart_number,
            symptoms=truncate_symptoms(record.symptoms),
            created_at=record.created_at,
        )
        for record in records
    ]
    return MedicalRecordListResponse(items=items)


# REQ-MDR-003 진료기록 상세 조회
@router.get("/medical-records/{record_id}", response_model=MedicalRecordDetailResponse)
async def get_medical_record_detail(
    record_id: int,
    service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    record = await service.get_by_id(record_id)
    xray_image_url = record.xray_images[0].image_url if record.xray_images else ""
    return MedicalRecordDetailResponse(
        id=record.id,
        chart_number=record.chart_number,
        symptoms=record.symptoms,
        xray_image_url=xray_image_url,
        created_at=record.created_at,
    )
