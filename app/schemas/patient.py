from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.user import Gender


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=0, le=130)
    gender: Gender
    phone_number: str = Field(min_length=1, max_length=20)


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    phone_number: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def require_update_field(self):
        if self.name is None and self.phone_number is None:
            raise ValueError("수정할 이름 또는 연락처를 입력해주세요.")
        return self


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str
    created_at: datetime
    updated_at: datetime | None


class MedicalRecordListResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    created_at: datetime


class MedicalRecordDetailResponse(MedicalRecordListResponse):
    xray_image_url: str | None
