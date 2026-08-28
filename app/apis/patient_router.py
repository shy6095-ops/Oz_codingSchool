from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from starlette.responses import Response

from app.apis.deps import get_current_medical_user, get_current_user, get_patient_service
from app.models.user import Gender, User
from app.schemas.patient import (
    MedicalRecordCreateResponse,
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
    MedicalRecordListResponse,
    PatientCreateRequest,
    PatientListResponse,
    PatientResponse,
    PatientUpdateRequest,
    XrayImageResponse,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreateRequest,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_medical_user)],
):
    return await service.create_patient(body)


@router.get("", response_model=PatientListResponse)
async def get_patient_list(
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
    keyword: Annotated[str | None, Query(max_length=30)] = None,
    gender: Gender | None = None,
    min_age: Annotated[int | None, Query(ge=0, le=150)] = None,
    max_age: Annotated[int | None, Query(ge=0, le=150)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, patients = await service.get_patient_list(
        keyword=keyword, gender=gender, min_age=min_age, max_age=max_age,
        page=page, size=size,
    )
    return PatientListResponse(items=patients, total=total, page=page, size=size)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await service.get_patient(patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    body: PatientUpdateRequest,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await service.update_patient(patient_id, body)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    await service.delete_patient(patient_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{patient_id}/medical-records",
    response_model=MedicalRecordCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_medical_record(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    uploader: Annotated[User, Depends(get_current_medical_user)],
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    xray_image: Annotated[UploadFile, File()],
):
    record, image = await service.create_medical_record(
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        xray_image=xray_image,
        uploader=uploader,
    )
    return MedicalRecordCreateResponse(
        id=record.id,
        patient_id=record.patient_id,
        chart_number=record.chart_number,
        symptoms=record.symptoms,
        xray_image_url=image.image_url,
        created_at=record.created_at,
    )


@router.get("/{patient_id}/medical-records", response_model=MedicalRecordListResponse)
async def get_medical_record_list(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, records = await service.get_medical_record_list(
        patient_id=patient_id, page=page, size=size
    )
    items = [
        MedicalRecordListItem(
            id=record.id,
            chart_number=record.chart_number,
            symptoms_preview=record.symptoms[:100],
            created_at=record.created_at,
        )
        for record in records
    ]
    return MedicalRecordListResponse(items=items, total=total, page=page, size=size)


@router.get(
    "/{patient_id}/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
)
async def get_medical_record(
    patient_id: int,
    record_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    record = await service.get_medical_record(
        patient_id=patient_id, record_id=record_id
    )
    return MedicalRecordDetailResponse(
        id=record.id,
        patient_id=record.patient_id,
        chart_number=record.chart_number,
        symptoms=record.symptoms,
        xray_images=[XrayImageResponse.model_validate(image) for image in record.xray_images],
        created_at=record.created_at,
    )
