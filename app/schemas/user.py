from pydantic import BaseModel, Field

from app.models.user import Department, Role


class UpdateUserRoleRequest(BaseModel):
    role: Role

class UpdateMyProfileRequest(BaseModel):
    department: Department | None = None
    phone_number: str | None = Field(
        default=None,
        max_length=20,
    )

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )