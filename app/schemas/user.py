from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import Department, Gender, Role

# bcrypt는 72바이트를 초과하는 부분을 조용히 잘라버리므로, 한글 등 멀티바이트 비밀번호가
# 의도치 않게 잘리지 않도록 문자 수가 아닌 UTF-8 바이트 길이로 상한을 검증한다.
PASSWORD_MAX_BYTES = 72


def _validate_password_byte_length(value: str) -> str:
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"비밀번호는 UTF-8 기준 {PASSWORD_MAX_BYTES}바이트를 초과할 수 없습니다.")
    return value


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=20)
    department: Department
    gender: Gender
    phone_number: str = Field(min_length=1, max_length=20)

    _validate_password = field_validator("password")(_validate_password_byte_length)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[UserListItem]


class UserMeResponse(BaseModel):
    name: str
    email: EmailStr
    department: Department
    gender: Gender
    phone_number: str
    role: Role

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    department: Department | None = None
    phone_number: str | None = Field(default=None, min_length=1, max_length=20)


class RoleUpdateRequest(BaseModel):
    role: Role


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    _validate_new_password = field_validator("new_password")(_validate_password_byte_length)
