from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Department, Gender, Role

# bcrypt는 72바이트를 초과하는 부분을 조용히 잘라버리므로, 한글 등 멀티바이트 비밀번호가
# 의도치 않게 잘리지 않도록 문자 수가 아닌 UTF-8 바이트 길이로 상한을 검증한다.
PASSWORD_MAX_BYTES = 72


def _validate_password_byte_length(value: str) -> str:
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"비밀번호는 UTF-8 기준 {PASSWORD_MAX_BYTES}바이트를 초과할 수 없습니다.")
    return value


# ---------- 요청 스키마 ----------

class UserSignupRequest(BaseModel):
    """REQ-USER-001 회원가입"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=20)
    department: Department
    gender: Gender
    phone_number: str = Field(max_length=20, pattern=r"^01[016789]-?\d{3,4}-?\d{4}$")

    _validate_password = field_validator("password")(_validate_password_byte_length)


class UserLoginRequest(BaseModel):
    """REQ-USER-002 로그인"""

    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    """REQ-USER-007 회원 정보 수정 (Partial) — 부서, 휴대폰 번호만 수정 가능"""

    department: Department | None = None
    phone_number: str | None = Field(
        default=None, max_length=20, pattern=r"^01[016789]-?\d{3,4}-?\d{4}$"
    )


class PasswordChangeRequest(BaseModel):
    """REQ-USER-008 비밀번호 변경"""

    current_password: str
    new_password: str = Field(min_length=8, max_length=64)

    _validate_new_password = field_validator("new_password")(_validate_password_byte_length)


class RoleUpdateRequest(BaseModel):
    """REQ-USER-005 회원 권한 변경 (Admin 전용)"""

    role: Role


# ---------- 응답 스키마 ----------

class UserResponse(BaseModel):
    """REQ-USER-004 / REQ-USER-006 회원 조회 공통 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool
    created_at: datetime


class UserListResponse(BaseModel):
    """REQ-USER-004 회원 목록 조회"""

    total: int
    items: list[UserResponse]


class TokenResponse(BaseModel):
    """NFR-USER-001 — 리프레시 토큰은 http_only 쿠키로 전달하므로 바디에는 액세스 토큰만"""

    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
