from fastapi import APIRouter, Cookie, Response, status

from app.apis.dependencies import DatabaseSession
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.schemas.user import AccessTokenResponse, LoginRequest, UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/api/v1/auth",
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Sign Up")
async def signup(payload: UserCreate, db: DatabaseSession) -> UserResponse:
    return await UserService(UserRepository(db)).create_user(payload)


@router.post("/login", response_model=AccessTokenResponse, summary="Log In")
async def login(payload: LoginRequest, response: Response, db: DatabaseSession) -> AccessTokenResponse:
    _, access_token, refresh_token = await AuthService(UserRepository(db)).login(payload)
    set_refresh_cookie(response, refresh_token)
    return AccessTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=AccessTokenResponse, summary="Refresh Access Token")
async def refresh_access_token(
    response: Response,
    db: DatabaseSession,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE_NAME),
) -> AccessTokenResponse:
    if not refresh_token:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 없습니다.")
    access_token, new_refresh_token = await AuthService(UserRepository(db)).refresh(refresh_token)
    set_refresh_cookie(response, new_refresh_token)
    return AccessTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log Out")
async def logout(
    response: Response,
    db: DatabaseSession,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_TOKEN_COOKIE_NAME),
) -> Response:
    await AuthService(UserRepository(db)).logout(refresh_token)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path="/api/v1/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
