from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Gender


PHONE_PATTERN = r"^01[016789]-?\d{3,4}-?\d{4}$"


class PatientCreate(BaseModel):
    """REQ-PTNT-001 환자 정보 등록"""

    name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=0, le=150)
    gender: Gender
    phone: str = Field(max_length=20, pattern=PHONE_PATTERN)


class PatientUpdate(BaseModel):
    """REQ-PTNT-004 환자 정보 수정 — 이름, 연락처만 수정 가능"""

    name: str | None = Field(default=None, min_length=1, max_length=30)
    phone: str | None = Field(default=None, max_length=20, pattern=PHONE_PATTERN)


class PatientResponse(BaseModel):
    """REQ-PTNT-001 / REQ-PTNT-002 / REQ-PTNT-004 공통 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    gender: Gender
    phone: str
    created_at: datetime
    updated_at: datetime | None


class PatientListResponse(BaseModel):
    """REQ-PTNT-002 환자 목록 조회"""

    total: int
    items: list[PatientResponse]


class PatientDetailResponse(BaseModel):
    """REQ-PTNT-003 환자 정보 상세 조회"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    gender: Gender
    phone: str
    age: int
