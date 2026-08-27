from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    payload_expiry,
    token_hash,
    utcnow,
    verify_password,
)
from app.models.auth_token import RefreshSession, RevokedAccessToken
from app.models.user import Department, Gender, Role, User
from app.schemas.user import (
    AdminRoleUpdateRequest,
    PasswordUpdateRequest,
    ProfileUpdateRequest,
    UserSignupRequest,
)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def create_user(
    db: AsyncSession,
    payload: UserSignupRequest,
    *,
    role: Role = Role.PENDING,
) -> User:
    user = User(
        email=str(payload.email).lower(),
        hashed_password=await hash_password(payload.password),
        name=payload.name,
        department=payload.department,
        gender=payload.gender,
        phone_number=payload.phone_number,
        role=role,
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일 또는 휴대폰 번호입니다.") from exc
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not await verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 일치하지 않습니다.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 사용자입니다.")
    return user


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    session = RefreshSession(
        user_id=user.id,
        token_hash=token_hash(refresh_token),
        expires_at=utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS),
    )
    db.add(session)
    await db.commit()
    return access_token, refresh_token


async def rotate_refresh_token(
    db: AsyncSession, user: User, refresh_token: str
) -> tuple[str, str]:
    session = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash(refresh_token),
            RefreshSession.user_id == user.id,
            RefreshSession.expires_at > utcnow(),
        )
    )
    if session is None:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 리프레시 토큰입니다.")
    await db.delete(session)
    await db.flush()
    return await issue_tokens(db, user)


async def update_profile(
    db: AsyncSession, user: User, payload: ProfileUpdateRequest
) -> User:
    if payload.phone_number is not None and payload.phone_number != user.phone_number:
        existing = await db.scalar(
            select(User.id).where(User.phone_number == payload.phone_number, User.id != user.id)
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="이미 사용 중인 휴대폰 번호입니다.")
        user.phone_number = payload.phone_number
    if payload.department is not None:
        user.department = payload.department
    await db.commit()
    await db.refresh(user)
    return user


async def update_password(
    db: AsyncSession, user: User, payload: PasswordUpdateRequest
) -> None:
    if not await verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="기존 비밀번호가 일치하지 않습니다.")
    user.hashed_password = await hash_password(payload.new_password)
    await db.commit()


async def revoke_access_token(db: AsyncSession, user: User, access_token: str) -> None:
    payload_exp = payload_expiry(decode_access_token(access_token))
    existing = await db.scalar(
        select(RevokedAccessToken).where(
            RevokedAccessToken.token_hash == token_hash(access_token)
        )
    )
    if existing is None:
        db.add(
            RevokedAccessToken(
                user_id=user.id,
                token_hash=token_hash(access_token),
                expires_at=payload_exp,
            )
        )


async def logout(db: AsyncSession, user: User, access_token: str, refresh_token: str | None) -> None:
    await revoke_access_token(db, user, access_token)
    if refresh_token:
        await db.execute(
            delete(RefreshSession).where(RefreshSession.token_hash == token_hash(refresh_token))
        )
    await db.commit()


async def delete_me(db: AsyncSession, user: User, access_token: str) -> None:
    await revoke_access_token(db, user, access_token)
    await db.flush()
    await db.delete(user)
    await db.commit()


async def list_users(
    db: AsyncSession, query: str | None, department: Department | None
) -> list[User]:
    statement = select(User)
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
    if department:
        statement = statement.where(User.department == department)
    result = await db.scalars(statement.order_by(User.id))
    return list(result)


async def update_roles(
    db: AsyncSession, admin: User, payload: AdminRoleUpdateRequest
) -> list[User]:
    if admin.id in payload.user_ids:
        raise HTTPException(status_code=400, detail="본인 권한은 변경할 수 없습니다.")
    users = list(
        await db.scalars(select(User).where(User.id.in_(payload.user_ids)).order_by(User.id))
    )
    if len(users) != len(payload.user_ids):
        raise HTTPException(status_code=404, detail="권한 변경 대상 회원을 찾을 수 없습니다.")
    for user in users:
        user.role = payload.role
    await db.commit()
    return users


async def bootstrap_admin(db: AsyncSession) -> None:
    if not settings.bootstrap_admin_is_configured:
        return
    assert settings.BOOTSTRAP_ADMIN_EMAIL is not None
    assert settings.BOOTSTRAP_ADMIN_PASSWORD is not None
    assert settings.BOOTSTRAP_ADMIN_NAME is not None
    assert settings.BOOTSTRAP_ADMIN_PHONE_NUMBER is not None
    assert settings.BOOTSTRAP_ADMIN_DEPARTMENT is not None
    assert settings.BOOTSTRAP_ADMIN_GENDER is not None
    if await get_user_by_email(db, settings.BOOTSTRAP_ADMIN_EMAIL):
        return
    try:
        payload = UserSignupRequest(
            email=settings.BOOTSTRAP_ADMIN_EMAIL,
            password=settings.BOOTSTRAP_ADMIN_PASSWORD,
            name=settings.BOOTSTRAP_ADMIN_NAME,
            phone_number=settings.BOOTSTRAP_ADMIN_PHONE_NUMBER,
            department=Department(settings.BOOTSTRAP_ADMIN_DEPARTMENT),
            gender=Gender(settings.BOOTSTRAP_ADMIN_GENDER),
        )
    except ValueError as exc:
        raise RuntimeError("관리자 초기화 환경변수 형식이 올바르지 않습니다.") from exc
    await create_user(db, payload, role=Role.ADMIN)
