from fastapi import HTTPException, status

from app.core.storage import delete_local_file
from app.models.patient import Patient
from app.models.user import Gender
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, repository: PatientRepository):
        self.repository = repository

    # REQ-PTNT-001 환자 정보 등록
    async def create(self, data: PatientCreate) -> Patient:
        patient = Patient(
            name=data.name, age=data.age, gender=data.gender, phone=data.phone
        )
        return await self.repository.create(patient)

    # REQ-PTNT-002 환자 목록 조회
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
        return await self.repository.get_list(
            search=search,
            gender=gender,
            min_age=min_age,
            max_age=max_age,
            offset=offset,
            limit=limit,
        )

    # REQ-PTNT-003 환자 정보 상세 조회
    async def get_by_id(self, patient_id: int) -> Patient:
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 환자를 찾을 수 없습니다.",
            )
        return patient

    # REQ-PTNT-004 환자 정보 수정 (Partial: 이름, 연락처만)
    async def update(self, patient_id: int, data: PatientUpdate) -> Patient:
        patient = await self.get_by_id(patient_id)
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목을 하나 이상 입력해주세요.",
            )
        return await self.repository.update(patient, **fields)

    # REQ-PTNT-005 환자 정보 삭제 (진료기록·X-Ray 이미지까지 cascade 삭제)
    async def delete(self, patient_id: int) -> None:
        patient = await self.repository.get_by_id_with_relations(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 환자를 찾을 수 없습니다.",
            )

        for record in patient.medical_records:
            for xray in record.xray_images:
                delete_local_file(xray.image_url)

        await self.repository.delete(patient)
