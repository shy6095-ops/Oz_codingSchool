from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import PasswordChangeRequest, UserCreate, UserRoleUpdate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, payload: UserCreate) -> User:
        if await self.repository.get_by_email(str(payload.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
        if await self.repository.get_by_phone_number(payload.phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 휴대폰 번호입니다.")
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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 회원 정보입니다.") from error

    async def update_user(self, user: User, payload: UserUpdate) -> User:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 정보가 없습니다.")
        if "phone_number" in values and values["phone_number"] != user.phone_number:
            existing = await self.repository.get_by_phone_number(values["phone_number"])
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 휴대폰 번호입니다.")
        for field, value in values.items():
            setattr(user, field, value)
        user = await self.repository.save(user)
        await self.repository.db.commit()
        return user

    async def change_password(self, user: User, payload: PasswordChangeRequest) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 일치하지 않습니다.")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="새 비밀번호는 기존 비밀번호와 달라야 합니다.")
        user.hashed_password = hash_password(payload.new_password)
        await self.repository.db.commit()

    async def change_role(self, user: User, payload: UserRoleUpdate) -> User:
        user.role = payload.role
        user = await self.repository.save(user)
        await self.repository.db.commit()
        return user

    async def delete_user(self, user: User) -> None:
        await self.repository.delete(user)
        await self.repository.db.commit()
