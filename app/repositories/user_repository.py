from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import Department, Gender, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_active_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_users(
        self, keyword: str | None, department: Department | None, offset: int, limit: int
    ) -> tuple[int, list[User]]:
        filters = []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
        if department:
            filters.append(User.department == department)

        statement = select(User).where(*filters).order_by(User.id.desc())
        count_statement = select(func.count()).select_from(User).where(*filters)
        total = (await self.db.execute(count_statement)).scalar_one()
        users = (await self.db.execute(statement.offset(offset).limit(limit))).scalars().all()
        return total, list(users)

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

    async def create_refresh_token(
        self, user_id: int, jti: str, expires_at: datetime
    ) -> RefreshToken:
        refresh_token = RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at)
        self.db.add(refresh_token)
        await self.db.flush()
        return refresh_token

    async def get_valid_refresh_token(self, jti: str, user_id: int) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.jti == jti,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, jti: str) -> None:
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
            refresh_token.revoked = True

    async def save(self, user: User) -> User:
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
