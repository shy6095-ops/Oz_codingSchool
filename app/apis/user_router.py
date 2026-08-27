from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.apis.deps import (
    get_current_admin,
    get_current_user,
    get_refresh_user_id,
    get_user_service,
)
from app.core.security import REFRESH_TOKEN_EXPIRE_DAYS
from app.models.user import Department, User
from app.schemas.user import (
    MessageResponse,
    PasswordChangeRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserListResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
    UserUpdateRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])

REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    # NFR-USER-001: 리프레시 토큰은 클라이언트에서 접근 불가하도록 http_only 쿠키로 전달
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/api/v1/users/token",
    )


# REQ-USER-001 회원가입
@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserSignupRequest,
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.signup(body)


# REQ-USER-002 로그인
@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    response: Response,
    service: Annotated[UserService, Depends(get_user_service)],
):
    access_token, refresh_token = await service.login(body.email, body.password)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


# NFR-USER-001 액세스 토큰 재발급
@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    user_id: Annotated[int, Depends(get_refresh_user_id)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    refresh_token = request.cookies.get("refresh_token", "")
    access_token = await service.reissue_access_token(user_id, refresh_token)
    return TokenResponse(access_token=access_token)


# REQ-USER-003 로그아웃 (서버에 저장된 리프레시 토큰까지 실제로 무효화)
@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    await service.logout(current_user)
    response.delete_cookie(key="refresh_token", path="/api/v1/users/token")
    return MessageResponse(message="로그아웃 되었습니다.")


# REQ-USER-006 마이페이지 조회
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


# REQ-USER-007 회원 정보 수정 (Partial)
@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.update_me(current_user, body)


# REQ-USER-008 비밀번호 변경
@router.patch("/me/password", response_model=MessageResponse)
async def change_password(
    body: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    await service.change_password(current_user, body)
    return MessageResponse(message="비밀번호가 변경되었습니다.")


# REQ-USER-009 회원 탈퇴
@router.delete("/me", response_model=MessageResponse)
async def withdraw(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    await service.withdraw(current_user)
    response.delete_cookie(key="refresh_token", path="/api/v1/users/token")
    return MessageResponse(message="회원 탈퇴가 완료되었습니다.")


# REQ-USER-004 회원 목록 조회 (Admin)
@router.get("", response_model=UserListResponse)
async def get_user_list(
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(get_current_admin)],
    search: Annotated[str | None, Query(description="이메일 또는 이름 검색")] = None,
    department: Annotated[Department | None, Query(description="부서 필터")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, users = await service.get_user_list(
        search=search, department=department, offset=offset, limit=limit
    )
    return UserListResponse(total=total, items=users)


# REQ-USER-005 회원 권한 변경 (Admin)
@router.patch("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: int,
    body: RoleUpdateRequest,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(get_current_admin)],
):
    return await service.change_role(user_id, body.role)
