from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.models.user import Gender
from app.schemas.patient import (
    MedicalRecordDetailResponse,
    MedicalRecordListResponse,
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)
from app.services.patient_service import PatientService


router = APIRouter(prefix="/api/v1", tags=["patients"])


def get_patient_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientService:
    return PatientService(session)


@router.post("/patients", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreateRequest,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.create_patient(body)


@router.get("/patients", response_model=list[PatientResponse])
async def list_patients(
    service: Annotated[PatientService, Depends(get_patient_service)],
    name: Annotated[str | None, Query(max_length=30)] = None,
    gender: Gender | None = None,
    min_age: Annotated[int | None, Query(ge=0, le=130)] = None,
    max_age: Annotated[int | None, Query(ge=0, le=130)] = None,
):
    return await service.list_patients(name, gender, min_age, max_age)


@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.get_patient_response(patient_id)


@router.patch("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    body: PatientUpdateRequest,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.update_patient(patient_id, body)


@router.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    await service.delete_patient(patient_id)


@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=list[MedicalRecordListResponse],
)
async def list_medical_records(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.list_medical_records(patient_id)


@router.post(
    "/medical-records",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_medical_record(
    patient_id: Annotated[int, Form(gt=0)],
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    xray_image: Annotated[UploadFile | None, File()] = None,
):
    return await service.create_medical_record(patient_id, chart_number, symptoms, xray_image)


@router.get("/medical-records/{record_id}", response_model=MedicalRecordDetailResponse)
async def get_medical_record(
    record_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.get_medical_record(record_id)
