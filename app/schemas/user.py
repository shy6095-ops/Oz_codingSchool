import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.user import Department, Gender, Role

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$"
)
PHONE_PATTERN = re.compile(r"^\d{10,11}$")


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=20)
    department: Department
    gender: Gender
    phone_number: str

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("이름을 입력해주세요.")
        return normalized

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.replace("-", "")
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("휴대폰 번호는 숫자 10~11자리여야 합니다.")
        return normalized


class UserSignupRequest(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.fullmatch(value):
            raise ValueError(
                "비밀번호는 대소문자, 특수문자, 숫자를 각 1개씩 포함한 8자리 이상이어야 합니다."
            )
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    department: Department | None = None
    phone_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.replace("-", "")
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("휴대폰 번호는 숫자 10~11자리여야 합니다.")
        return normalized

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("수정할 정보를 하나 이상 입력해주세요.")
        return self


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.fullmatch(value):
            raise ValueError(
                "비밀번호는 대소문자, 특수문자, 숫자를 각 1개씩 포함한 8자리 이상이어야 합니다."
            )
        return value


class AdminRoleUpdateRequest(BaseModel):
    user_ids: list[int] = Field(min_length=1)
    role: Role

    @field_validator("user_ids")
    @classmethod
    def unique_user_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("중복된 회원 ID는 선택할 수 없습니다.")
        return value
