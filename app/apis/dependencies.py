from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import decode_access_token
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository

DatabaseSession = Annotated[AsyncSession, Depends(async_get_db)]


async def get_current_user(
    db: DatabaseSession, authorization: Annotated[str | None, Header()] = None
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 없거나 유효하지 않습니다.")
    payload = decode_access_token(authorization.removeprefix("Bearer "))
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 없거나 유효하지 않습니다.")
    user = await UserRepository(db).get_active_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 정보가 없거나 유효하지 않습니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
