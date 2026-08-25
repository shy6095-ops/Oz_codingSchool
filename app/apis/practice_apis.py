import re
from itertools import count

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/practice_api", tags=["practice"])


user_list = [
    {
        "id": 1,
        "name": "홍길동",
        "age": 24,
        "email": "gildong24@example.com",
        "password": "Password1234!!",
    },
    {
        "id": 2,
        "name": "장문복",
        "age": 21,
        "email": "moonluck12@example.com",
        "password": "Check1321!",
    },
    {
        "id": 3,
        "name": "임우진",
        "age": 31,
        "email": "limousine33@example.com",
        "password": "lwsPAssword12@",
    },
]

next_user_id = count(max(user["id"] for user in user_list) + 1)

# 이메일 형식을 검사하기 위한 정규표현식
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
# 소문자, 대문자, 특수문자를 포함한 8~20자 비밀번호 형식
PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,20}$"
)


def get_user(user_id: int) -> dict:
    """사용자 ID로 회원 정보를 조회합니다."""
    user = next((user for user in user_list if user["id"] == user_id), None)

    if user is None:
        raise HTTPException(404, "존재하지 않는 회원입니다.")

    return user


def check_email(email: str, current_id: int | None = None):
    """다른 회원이 이미 사용 중인 이메일인지 확인합니다."""
    if any(
        user["email"] == email and user["id"] != current_id
        for user in user_list
    ):
        raise HTTPException(409, "이미 사용 중인 이메일입니다.")


class UserResponse(BaseModel):
    """API 응답에 포함할 사용자 정보입니다. 비밀번호는 제외합니다."""
    id: int
    name: str
    age: int
    email: str


class UserCreate(BaseModel):
    """회원가입 요청 데이터와 입력값 검증 규칙입니다."""
    name: str = Field(min_length=2, max_length=10)
    age: int = Field(ge=14)
    email: str = Field(max_length=30)  # 이메일 최대 30자
    password: str = Field(min_length=8, max_length=20)  # 비밀번호 길이 제한

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str):
        if not EMAIL_RE.fullmatch(value):
            raise HTTPException("올바른 이메일 형식이 아닙니다.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        if not PASSWORD_RE.fullmatch(value):
            raise HTTPException("비밀번호 형식이 올바르지 않습니다.")
        return value


class UserUpdate(BaseModel):
    """회원정보 수정 요청 데이터입니다. 입력한 항목만 수정합니다."""
    age: int | None = Field(default=None, ge=14)
    email: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if value is not None and not EMAIL_RE.fullmatch(value):
            raise HTTPException("올바른 이메일 형식이 아닙니다.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None):
        if value is not None and not PASSWORD_RE.fullmatch(value):
            raise HTTPException("비밀번호 형식이 올바르지 않습니다.")
        return value


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="회원 목록 조회",
    description="등록된 모든 회원의 정보를 조회합니다.",
)
def read_users():
    return user_list


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="회원 상세 조회",
    description="회원 ID로 특정 회원의 정보를 조회합니다.",
)
def read_user(user_id: int):
    return get_user(user_id)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 가입",
    description="새로운 회원을 등록합니다.",
)
def create_user(data: UserCreate):
    check_email(data.email)

    user = {
        "id": next(next_user_id),
        **data.model_dump(),
    }
    user_list.append(user)

    return user


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="회원 정보 수정",
    description="회원 ID에 해당하는 회원 정보를 수정합니다.",
)
def update_user(user_id: int, data: UserUpdate):
    user = get_user(user_id)
    updates = data.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(400, "수정할 항목을 하나 이상 입력해야 합니다.")

    if "email" in updates:
        check_email(updates["email"], user_id)

    user.update(updates)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
    description="회원 ID에 해당하는 회원을 삭제합니다.",
)
def delete_user(user_id: int):
    user_list.remove(get_user(user_id))