from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_medical_staff, get_current_user
from app.core.db.databases import async_get_db
from app.models.user import Gender, User
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import (
    PatientCreate,
    PatientDetailResponse,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


def get_patient_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientService:
    return PatientService(PatientRepository(session))


# REQ-PTNT-001 환자 정보 등록 (사내 의료인 전용)
@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_medical_staff)],
):
    return await service.create(body)


# REQ-PTNT-002 환자 목록 조회
@router.get("", response_model=PatientListResponse)
async def get_patient_list(
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
    search: Annotated[str | None, Query(description="이름 검색")] = None,
    gender: Annotated[Gender | None, Query()] = None,
    min_age: Annotated[int | None, Query(ge=0)] = None,
    max_age: Annotated[int | None, Query(ge=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, patients = await service.get_list(
        search=search,
        gender=gender,
        min_age=min_age,
        max_age=max_age,
        offset=offset,
        limit=limit,
    )
    return PatientListResponse(total=total, items=patients)


# REQ-PTNT-003 환자 정보 상세 조회
@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient_detail(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await service.get_by_id(patient_id)


# REQ-PTNT-004 환자 정보 수정 (Partial: 이름, 연락처만)
@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    body: PatientUpdate,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await service.update(patient_id, body)


# REQ-PTNT-005 환자 정보 삭제 (진료기록·X-Ray 이미지까지 cascade 삭제)
@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    service: Annotated[PatientService, Depends(get_patient_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    await service.delete(patient_id)
