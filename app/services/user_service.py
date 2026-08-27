from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, payload: UserCreate) -> User:
        if await self.repository.get_by_email(str(payload.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
        try:
            user = await self.repository.create(
                email=str(payload.email),
                hashed_password=hash_password(payload.password),
                name=payload.name,
                phone_number=payload.phone_number,
                gender=payload.gender,
                department=payload.department,
            )
            await self.repository.db.commit()
            return user
        except IntegrityError as error:
            await self.repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다."
            ) from error

    async def update_user(self, user: User, payload: UserUpdate) -> User:
        if payload.name is None and payload.password is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 정보가 없습니다.")
        if payload.name is not None:
            user.name = payload.name
        if payload.password is not None:
            user.hashed_password = hash_password(payload.password)
        user.updated_at = datetime.now(UTC)
        user = await self.repository.save(user)
        await self.repository.db.commit()
        return user

    async def delete_user(self, user: User) -> None:
        user.is_active = False
        await self.repository.db.commit()
