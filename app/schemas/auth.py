from pydantic import BaseModel, Field

from app.models.user import Department, Gender


class SignUpRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(max_length=20)
    department: Department
    gender: Gender
    phone_number: str = Field(max_length=20)

class LoginRequest(BaseModel):
    email: str
    password: str