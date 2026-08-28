from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Gender


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=0, le=150)
    gender: Gender
    phone: str = Field(max_length=20, pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    phone: str | None = Field(default=None, max_length=20, pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    age: int
    gender: Gender
    phone: str
    created_at: datetime
    updated_at: datetime | None


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    size: int


class MedicalRecordCreateResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str
    created_at: datetime


class MedicalRecordListItem(BaseModel):
    id: int
    chart_number: str
    symptoms_preview: str
    created_at: datetime


class MedicalRecordListResponse(BaseModel):
    items: list[MedicalRecordListItem]
    total: int
    page: int
    size: int


class XrayImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_url: str
    shooting_datetime: datetime


class MedicalRecordDetailResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_images: list[XrayImageResponse]
    created_at: datetime
