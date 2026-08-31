from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_medical_user, get_current_user
from app.core.db.databases import async_get_db
from app.worker.models.user import Gender, User
from app.schemas.patient import (
    MedicalRecordDetailResponse,
    MedicalRecordPageResponse,
    PatientCreateRequest,
    PatientListResponse,
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
    _: Annotated[User, Depends(get_current_medical_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.create_patient(body)


@router.get("/patients", response_model=PatientListResponse)
async def list_patients(
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    name: Annotated[str | None, Query(max_length=30)] = None,
    gender: Gender | None = None,
    min_age: Annotated[int | None, Query(ge=0, le=130)] = None,
    max_age: Annotated[int | None, Query(ge=0, le=130)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, items = await service.list_patients(
        name, gender, min_age, max_age, page, size
    )
    return PatientListResponse(total=total, page=page, size=size, items=items)


@router.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.get_patient_response(patient_id)


@router.patch("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    body: PatientUpdateRequest,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.update_patient(patient_id, body)


@router.delete("/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    await service.delete_patient(patient_id)


@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=MedicalRecordPageResponse,
)
async def list_medical_records(
    patient_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, items = await service.list_medical_records(patient_id, page, size)
    return MedicalRecordPageResponse(total=total, page=page, size=size, items=items)


@router.post(
    "/patients/{patient_id}/medical-records",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_medical_record(
    patient_id: int,
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    current_user: Annotated[User, Depends(get_current_medical_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
    xray_image: Annotated[UploadFile | None, File()] = None,
):
    return await service.create_medical_record(
        patient_id, chart_number, symptoms, xray_image, current_user.id
    )


@router.get(
    "/patients/{patient_id}/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
)
async def get_medical_record(
    patient_id: int,
    record_id: int,
    _: Annotated[User, Depends(get_current_user)],
    service: Annotated[PatientService, Depends(get_patient_service)],
):
    return await service.get_medical_record(patient_id, record_id)
