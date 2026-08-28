from datetime import datetime

from pydantic import BaseModel


class MedicalRecordResponse(BaseModel):
    """REQ-MDR-001 진료기록 등록 응답"""

    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str
    created_at: datetime


class MedicalRecordListItem(BaseModel):
    """REQ-MDR-002 진료기록 목록 조회 항목 (증상은 100자 초과 시 말줄임)"""

    id: int
    chart_number: str
    symptoms: str
    created_at: datetime


class MedicalRecordListResponse(BaseModel):
    items: list[MedicalRecordListItem]


class MedicalRecordDetailResponse(BaseModel):
    """REQ-MDR-003 진료기록 상세 조회"""

    id: int
    chart_number: str
    symptoms: str
    xray_image_url: str
    created_at: datetime
