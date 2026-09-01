import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import AsyncSessionLocal
from app.core.security import hash_password, verify_password
from app.worker.models.user import Department, Gender, Role, User


logger = logging.getLogger(__name__)


async def ensure_test_user(
    session: AsyncSession,
    *,
    enabled: bool,
    email: str,
    password: str,
    name: str,
    phone_number: str,
) -> User | None:
    """명시적으로 활성화된 로컬 테스트 계정을 한 건으로 유지한다."""
    if not enabled:
        return None
    if not email or not password:
        raise ValueError(
            "BOOTSTRAP_TEST_USER_EMAIL과 BOOTSTRAP_TEST_USER_PASSWORD가 필요합니다."
        )

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name=name,
            department=Department.MEDICAL,
            gender=Gender.M,
            phone_number=phone_number,
            role=Role.STAFF,
            is_active=True,
        )
        session.add(user)
    else:
        if not verify_password(password, user.hashed_password):
            user.hashed_password = hash_password(password)
        user.name = name
        user.department = Department.MEDICAL
        user.phone_number = phone_number
        user.role = Role.STAFF
        user.is_active = True

    await session.commit()
    await session.refresh(user)
    return user


async def bootstrap_from_settings() -> None:
    async with AsyncSessionLocal() as session:
        user = await ensure_test_user(
            session,
            enabled=settings.BOOTSTRAP_TEST_USER_ENABLED,
            email=settings.BOOTSTRAP_TEST_USER_EMAIL,
            password=settings.BOOTSTRAP_TEST_USER_PASSWORD,
            name=settings.BOOTSTRAP_TEST_USER_NAME,
            phone_number=settings.BOOTSTRAP_TEST_USER_PHONE_NUMBER,
        )
    if user is not None:
        logger.info("로컬 테스트 계정이 준비되었습니다: %s", user.email)


def main() -> None:
    asyncio.run(bootstrap_from_settings())


if __name__ == "__main__":
    main()
