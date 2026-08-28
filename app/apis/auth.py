from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.core.dependencies import get_current_user
from app.schemas.user import ChangePasswordRequest, UpdateMyProfileRequest
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import hash_password, verify_password
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, SignUpRequest
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignUpRequest,
    db: AsyncSession = Depends(async_get_db),
):
    existing_user = await db.scalar(
        select(User).where(
            or_(
                User.email == payload.email,
                User.phone_number == payload.phone_number,
            )
        )
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일 또는 휴대폰 번호입니다.",
        )

    hashed_password = hash_password(payload.password)

    user = User(
        email=payload.email,
        hashed_password=hashed_password,
        name=payload.name,
        department=payload.department,
        gender=payload.gender,
        phone_number=payload.phone_number,
        role=Role.PENDING,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "회원가입이 완료되었습니다.",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }

@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(async_get_db),
):
    user = await db.scalar(
        select(User).where(User.email == payload.email)
    )

    if user is None or not verify_password(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
):
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없습니다.",
        )

    try:
        payload = decode_token(
            refresh_token,
            expected_token_type="refresh",
        )
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 유효하지 않습니다.",
        )

    user = await db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없거나 비활성화되었습니다.",
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "department": current_user.department,
        "gender": current_user.gender,
        "phone_number": current_user.phone_number,
        "role": current_user.role,
    }

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
    )

@router.patch("/me")
async def update_my_profile(
    payload: UpdateMyProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    if payload.department is None and payload.phone_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 정보를 하나 이상 입력해주세요.",
        )

    user = await db.get(User, current_user.id)

    if payload.phone_number is not None:
        existing_user = await db.scalar(
            select(User).where(
                User.phone_number == payload.phone_number,
                User.id != current_user.id,
            )
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 휴대폰 번호입니다.",
            )

        user.phone_number = payload.phone_number

    if payload.department is not None:
        user.department = payload.department

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "department": user.department,
        "phone_number": user.phone_number,
        "role": user.role,
    }

@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_my_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 기존 비밀번호와 달라야 합니다.",
        )

    user = await db.get(User, current_user.id)

    if not verify_password(
        payload.current_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기존 비밀번호가 올바르지 않습니다.",
        )

    user.hashed_password = hash_password(payload.new_password)

    await db.commit()

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
    )

@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    user = await db.get(User, current_user.id)

    await db.delete(user)
    await db.commit()

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
    )