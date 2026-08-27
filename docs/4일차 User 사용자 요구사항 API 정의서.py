"""
User API Implementation
FastAPI framework based implementation according to the User API Specification.
"""

from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query, Response, Cookie
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field


# ==========================================
# 1. Enums 및 Data Models (Pydantic Schema)
# ==========================================

class DepartmentEnum(str, Enum):
    RESEARCH = "연구"
    MEDICAL = "의료"
    DEVELOPMENT = "개발"


class GenderEnum(str, Enum):
    MALE = "M"
    FEMALE = "F"


class RoleEnum(str, Enum):
    WAITING = "대기자"
    STAFF = "스태프"
    ADMIN = "어드민"


# Requests
class UserSignUpRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    department: DepartmentEnum
    gender: GenderEnum
    phone: str = Field(..., example="010-1234-5678")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleUpdateRequest(BaseModel):
    role: RoleEnum


class UserUpdateRequest(BaseModel):
    department: Optional[DepartmentEnum] = None
    phone: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# Responses
class UserSignUpResponse(BaseModel):
    message: str
    user_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30분 (초 단위)


class UserResponse(BaseModel):
    user_id: int
    email: EmailStr
    name: str
    department: DepartmentEnum
    gender: GenderEnum
    phone: str
    is_active: bool = True


class MyProfileResponse(BaseModel):
    name: str
    email: EmailStr
    department: DepartmentEnum
    gender: GenderEnum
    phone: str
    role: RoleEnum


# ==========================================
# 2. Application Setup & Security Layer
# ==========================================

app = FastAPI(
    title="User API Service",
    description="REQ-USER 및 NFR 규격 준수 유저 관리 API",
    version="1.0.0"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Mock 인증 디펜던시 (JWT validation 및 Payload 식별자 검증)
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    # 토큰에서 user_id 추출 로직 구현부
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다."
        )
    return 1  # Dummy user_id


async def verify_admin_role(user_id: int = Depends(get_current_user_id)) -> int:
    # 관리자 권한(Admin) 검증 로직 구현부
    is_admin = True
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return user_id


# ==========================================
# 3. API Endpoints (Async implementation)
# ==========================================

# 2.1 회원 가입
@app.post(
    "/api/v1/users/signup",
    response_model=UserSignUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 가입 (REQ-USER-001)"
)
async def signup(user_data: UserSignUpRequest):
    return UserSignUpResponse(
        message="회원가입이 완료되었습니다.",
        user_id=1
    )


# 2.2 로그인
@app.post(
    "/api/v1/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="로그인 (REQ-USER-002, NFR-USER-001)"
)
async def login(credentials: UserLoginRequest, response: Response):
    # Refresh Token HttpOnly Cookie 설정 (유효기간 7일)
    mock_refresh_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    response.set_cookie(
        key="refresh_token",
        value=mock_refresh_token,
        httponly=True,
        path="/",
        max_age=604800,
        samesite="lax",
        secure=True
    )
    
    return LoginResponse(
        access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        token_type="bearer",
        expires_in=1800
    )


# 2.3 로그아웃
@app.post(
    "/api/v1/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="로그아웃 (REQ-USER-003)"
)
async def logout(
    response: Response,
    current_user: int = Depends(get_current_user_id)
):
    # HttpOnly Refresh Token 쿠키 만료 처리
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        path="/",
        max_age=0
    )
    return {"message": "성공적으로 로그아웃 되었습니다."}


# 2.4 회원 목록 조회 (Admin Only)
@app.get(
    "/api/v1/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="회원 목록 조회 (REQ-USER-004)"
)
async def get_users(
    search: Optional[str] = Query(None, description="이메일 또는 이름 검색"),
    department: Optional[DepartmentEnum] = Query(None, description="부서 필터링"),
    admin_id: int = Depends(verify_admin_role)
):
    return [
        UserResponse(
            user_id=1,
            email="user@example.com",
            name="홍길동",
            department=DepartmentEnum.DEVELOPMENT,
            gender=GenderEnum.MALE,
            phone="010-1234-5678",
            is_active=True
        )
    ]


# 2.5 회원 권한 변경 (Admin Only)
@app.patch(
    "/api/v1/users/{user_id}/role",
    status_code=status.HTTP_200_OK,
    summary="회원 권한 변경 (REQ-USER-005)"
)
async def update_user_role(
    user_id: int,
    role_data: RoleUpdateRequest,
    admin_id: int = Depends(verify_admin_role)
):
    return {"message": f"사용자 {user_id}의 권한이 {role_data.role.value}(으)로 변경되었습니다."}


# 2.6 마이페이지 조회
@app.get(
    "/api/v1/users/me",
    response_model=MyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="마이페이지 조회 (REQ-USER-006)"
)
async def get_my_profile(current_user: int = Depends(get_current_user_id)):
    return MyProfileResponse(
        name="홍길동",
        email="user@example.com",
        department=DepartmentEnum.DEVELOPMENT,
        gender=GenderEnum.MALE,
        phone="010-1234-5678",
        role=RoleEnum.WAITING
    )


# 2.7 회원 정보 수정 (Partial Update)
@app.patch(
    "/api/v1/users/me",
    status_code=status.HTTP_200_OK,
    summary="회원 정보 수정 (REQ-USER-007)"
)
async def update_my_profile(
    update_data: UserUpdateRequest,
    current_user: int = Depends(get_current_user_id)
):
    return {"message": "회원 정보가 수정되었습니다."}


# 2.8 비밀번호 변경
@app.patch(
    "/api/v1/users/me/password",
    status_code=status.HTTP_200_OK,
    summary="비밀번호 변경 (REQ-USER-008, NFR-USER-002)"
)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: int = Depends(get_current_user_id)
):
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


# 2.9 회원 탈퇴
@app.delete(
    "/api/v1/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴 (REQ-USER-009)"
)
async def delete_my_account(current_user: int = Depends(get_current_user_id)):
    return None