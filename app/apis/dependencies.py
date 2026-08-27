from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import decode_access_token, token_hash
from app.models.auth_token import RevokedAccessToken
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(
    access_token: Annotated[str, Depends(get_access_token)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    payload = decode_access_token(access_token)
    revoked = await db.scalar(
        select(RevokedAccessToken.id).where(
            RevokedAccessToken.token_hash == token_hash(access_token)
        )
    )
    if revoked is not None:
        raise HTTPException(status_code=401, detail="로그아웃된 토큰입니다.")

    user = await db.get(User, payload["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 사용자입니다.")
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return user


async def require_staff_or_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role is Role.PENDING:
        raise HTTPException(status_code=403, detail="승인 대기 중인 사용자입니다.")
    return user
