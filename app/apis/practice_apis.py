import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

router = APIRouter(prefix="/practice_api", tags=["Practice API"])

# ── 초기 데이터 ──────────────────────────────────────────────────────────────
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

# ── 정규표현식 ────────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,20}$"
)


# ── Pydantic 스키마 ───────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    age: int
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not (2 <= len(v) <= 10):
            raise ValueError("이름은 최소 2글자, 최대 10글자여야 합니다.")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 14:
            raise ValueError("나이는 최소 14세 이상이어야 합니다.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if len(v) > 30:
            raise ValueError("이메일은 최대 30자까지 허용됩니다.")
        if not EMAIL_REGEX.match(v):
            raise ValueError("유효하지 않은 이메일 형식입니다.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "비밀번호는 8~20자이며 대문자·소문자·특수문자를 각 1개 이상 포함해야 합니다."
            )
        return v


class UserUpdate(BaseModel):
    age: Optional[int] = None
    email: Optional[str] = None
    password: Optional[str] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 14:
            raise ValueError("나이는 최소 14세 이상이어야 합니다.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) > 30:
            raise ValueError("이메일은 최대 30자까지 허용됩니다.")
        if not EMAIL_REGEX.match(v):
            raise ValueError("유효하지 않은 이메일 형식입니다.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "비밀번호는 8~20자이며 대문자·소문자·특수문자를 각 1개 이상 포함해야 합니다."
            )
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UserUpdate":
        if self.age is None and self.email is None and self.password is None:
            raise ValueError("수정할 항목(age, email, password)을 하나 이상 입력해야 합니다.")
        return self


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
def _find_user(user_id: int) -> dict:
    for user in user_list:
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="해당 id의 회원을 찾을 수 없습니다.")


def _public(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password"}


# ── API 1: 전체 회원 목록 조회 (GET) ─────────────────────────────────────────
@router.get("/users", summary="전체 회원 목록 조회")
def get_users():
    return [_public(u) for u in user_list]


# ── API 2: 특정 회원 조회 (GET) ──────────────────────────────────────────────
@router.get("/users/{user_id}", summary="특정 회원 조회")
def get_user(user_id: int):
    return _public(_find_user(user_id))


# ── API 3: 회원 추가 (POST) ──────────────────────────────────────────────────
@router.post("/users", status_code=201, summary="회원 추가")
def create_user(body: UserCreate):
    if any(u["email"] == body.email for u in user_list):
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    new_id = max(u["id"] for u in user_list) + 1 if user_list else 1
    new_user = {
        "id": new_id,
        "name": body.name,
        "age": body.age,
        "email": body.email,
        "password": body.password,
    }
    user_list.append(new_user)
    return {"message": "회원이 추가되었습니다.", "user": _public(new_user)}


# ── API 4: 회원 정보 수정 (PATCH) ────────────────────────────────────────────
@router.patch("/users/{user_id}", summary="회원 정보 수정")
def update_user(user_id: int, body: UserUpdate):
    user = _find_user(user_id)

    if body.age is not None:
        user["age"] = body.age
    if body.email is not None:
        user["email"] = body.email
    if body.password is not None:
        user["password"] = body.password

    return {"message": "회원 정보가 수정되었습니다.", "user": _public(user)}


# ── API 5: 회원 삭제 (DELETE) ────────────────────────────────────────────────
@router.delete("/users/{user_id}", summary="회원 삭제")
def delete_user(user_id: int):
    user = _find_user(user_id)
    user_list.remove(user)
    return {"message": f"id={user_id} 회원이 삭제되었습니다."}