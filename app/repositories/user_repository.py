from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.models.user import Department, Role, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        *,
        search: str | None = None,
        department: Department | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[int, list[User]]:
        """REQ-USER-004: 이메일/이름 검색 + 부서 필터"""
        stmt = select(User)
        if search:
            stmt = stmt.where(
                or_(User.email.contains(search), User.name.contains(search))
            )
        if department:
            stmt = stmt.where(User.department == department)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(User.id).offset(offset).limit(limit)
        users = (await self.session.execute(stmt)).scalars().all()
        return total, list(users)

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_role(self, user: User, role: Role) -> User:
        user.role = role
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """REQ-USER-009: 회원 탈퇴 시 관련 정보 즉시 삭제"""
        await self.session.delete(user)
        await self.session.commit()
