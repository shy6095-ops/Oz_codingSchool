from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.dependencies import get_access_token, get_current_user, require_admin
from app.core.config import settings
from app.core.db.databases import async_get_db
from app.core.security import decode_refresh_token
from app.models.user import Department, User
from app.schemas.user import (
    AdminRoleUpdateRequest,
    AuthResponse,
    PasswordUpdateRequest,
    ProfileUpdateRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services import user_service

router = APIRouter(prefix="/api/v1", tags=["users"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        path="/api/v1/users",
    )


def auth_response(access_token: str, user: User) -> AuthResponse:
    return AuthResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        user=UserResponse.model_validate(user),
    )


@router.post("/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: UserSignupRequest, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> User:
    return await user_service.create_user(db, payload)


@router.post("/users/login", response_model=AuthResponse)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> AuthResponse:
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    access_token, refresh_token = await user_service.issue_tokens(db, user)
    set_refresh_cookie(response, refresh_token)
    return auth_response(access_token, user)


@router.post("/users/refresh", response_model=AuthResponse)
async def refresh(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(async_get_db),
) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="리프레시 토큰이 필요합니다.")
    payload = decode_refresh_token(refresh_token)
    user = await db.get(User, payload["user_id"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")
    access_token, new_refresh_token = await user_service.rotate_refresh_token(
        db, user, refresh_token
    )
    set_refresh_cookie(response, new_refresh_token)
    return auth_response(access_token, user)


@router.post("/users/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(async_get_db),
) -> Response:
    await user_service.logout(db, user, access_token, refresh_token)
    response.delete_cookie("refresh_token", path="/api/v1/users", secure=settings.SECURE_COOKIES, httponly=True, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/users/me", response_model=UserResponse)
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.patch("/users/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(async_get_db),
) -> User:
    return await user_service.update_profile(db, user, payload)


@router.patch("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_password(
    payload: PasswordUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(async_get_db),
) -> Response:
    await user_service.update_password(db, user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
    db: AsyncSession = Depends(async_get_db),
) -> Response:
    await user_service.delete_me(db, user, access_token)
    response.delete_cookie("refresh_token", path="/api/v1/users", secure=settings.SECURE_COOKIES, httponly=True, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    query: str | None = Query(default=None, max_length=255),
    department: Department | None = None,
) -> list[User]:
    return await user_service.list_users(db, query, department)


@router.patch("/admin/users/roles", response_model=list[UserResponse])
async def admin_update_roles(
    payload: AdminRoleUpdateRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> list[User]:
    return await user_service.update_roles(db, admin, payload)
