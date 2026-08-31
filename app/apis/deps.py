from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import decode_token
from app.models.user import Department, Role, User
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.user_repository import UserRepository
from app.services.prediction_service import PredictionService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> UserService:
    return UserService(UserRepository(session))


def get_prediction_service(
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PredictionService:
    return PredictionService(PredictionRepository(session))

async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    """액세스 토큰을 검증하고 현재 로그인 유저를 반환한다."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="액세스 토큰이 만료되었습니다.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )

    user = await UserRepository(session).get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 사용자입니다.",
        )
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """REQ-USER-004/005: Admin 권한 필요 API 전용"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


async def get_current_prediction_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """REQ-PRED-001/002: approved medical, development, or research users only."""
    allowed_departments = {Department.MEDICAL, Department.DEV, Department.RESEARCH}
    if current_user.role not in {Role.STAFF, Role.ADMIN} or (
        current_user.department not in allowed_departments
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인된 의료, 개발 또는 연구 부서 사용자만 수행할 수 있습니다.",
        )
    return current_user


def get_refresh_user_id(request: Request) -> int:
    """NFR-USER-001: http_only 쿠키의 리프레시 토큰을 검증한다."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 없습니다. 다시 로그인해주세요.",
        )
    try:
        return decode_token(token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 만료되었습니다. 다시 로그인해주세요.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다.",
        )
