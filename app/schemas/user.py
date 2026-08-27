from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Department, Gender, Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=20)
    phone_number: str = Field(min_length=1, max_length=20)
    gender: Gender
    department: Department

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name은 빈 문자열일 수 없습니다.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    department: Department | None = None
    phone_number: str | None = Field(default=None, min_length=1, max_length=20)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserRoleUpdate(BaseModel):
    role: Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    phone_number: str
    gender: Gender
    department: Department
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
