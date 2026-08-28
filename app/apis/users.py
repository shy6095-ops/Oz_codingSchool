from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.dependencies import require_admin
from app.models.user import Department, User
from app.schemas.user import UpdateUserRoleRequest


router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


@router.get("")
async def list_users(
    keyword: str | None = Query(default=None),
    department: Department | None = Query(default=None),
    db: AsyncSession = Depends(async_get_db),
    admin: User = Depends(require_admin),
):
    statement = select(User)

    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                User.email.like(pattern),
                User.name.like(pattern),
            )
        )

    if department:
        statement = statement.where(
            User.department == department
        )

    users = (await db.scalars(statement.order_by(User.id))).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "department": user.department,
            "gender": user.gender,
            "phone_number": user.phone_number,
            "is_active": user.is_active,
            "role": user.role,
        }
        for user in users
    ]

@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    db: AsyncSession = Depends(async_get_db),
    admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    user.role = payload.role

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }