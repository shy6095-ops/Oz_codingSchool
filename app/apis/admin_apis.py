from fastapi import APIRouter, HTTPException, Query, status

from app.apis.dependencies import AdminUser, DatabaseSession
from app.models.user import Department
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserListResponse, UserResponse, UserRoleUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])


@router.get("", response_model=UserListResponse, summary="List Users")
async def list_users(
    _: AdminUser,
    db: DatabaseSession,
    keyword: str | None = Query(default=None, max_length=255),
    department: Department | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> UserListResponse:
    total, users = await UserRepository(db).list_users(keyword, department, (page - 1) * size, size)
    return UserListResponse(total=total, items=users)


@router.patch("/{user_id}/role", response_model=UserResponse, summary="Change User Role")
async def change_user_role(
    user_id: int, payload: UserRoleUpdate, _: AdminUser, db: DatabaseSession
) -> UserResponse:
    repository = UserRepository(db)
    user = await repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return await UserService(repository).change_role(user, payload)
