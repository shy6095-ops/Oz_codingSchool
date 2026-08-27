from fastapi import APIRouter, Response, status

from app.apis.dependencies import CurrentUser, DatabaseSession
from app.schemas.user import PasswordChangeRequest, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse, summary="Read My Profile")
async def read_my_profile(current_user: CurrentUser) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Update My Profile")
async def update_my_profile(
    payload: UserUpdate, current_user: CurrentUser, db: DatabaseSession
) -> UserResponse:
    return await UserService(UserRepository(db)).update_user(current_user, payload)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change My Password")
async def change_my_password(
    payload: PasswordChangeRequest, current_user: CurrentUser, db: DatabaseSession
) -> Response:
    await UserService(UserRepository(db)).change_password(current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete My Account")
async def delete_my_account(current_user: CurrentUser, db: DatabaseSession) -> Response:
    await UserService(UserRepository(db)).delete_user(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
