from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserUpdateResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: DatabaseSession) -> User:
    return await UserService(UserRepository(db)).create_user(payload)


@router.get("/me", response_model=UserResponse)
async def read_my_profile(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserUpdateResponse)
async def update_my_profile(
    payload: UserUpdate, current_user: CurrentUser, db: DatabaseSession
) -> User:
    return await UserService(UserRepository(db)).update_user(current_user, payload)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(current_user: CurrentUser, db: DatabaseSession) -> Response:
    await UserService(UserRepository(db)).delete_user(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
