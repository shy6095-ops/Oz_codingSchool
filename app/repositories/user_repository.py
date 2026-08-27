from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Department, Gender, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        name: str,
        phone_number: str,
        gender: Gender,
        department: Department,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            phone_number=phone_number,
            gender=gender,
            department=department,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def save(self, user: User) -> User:
        await self.db.flush()
        await self.db.refresh(user)
        return user
