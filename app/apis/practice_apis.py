# app/apis/practice_apis.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(
    prefix="/practice_api",
    tags=["practice"]
)

class UserCreate(BaseModel):
    name: str
    age: int
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    email: EmailStr | None = None
    password: str | None = None

user_list = [
	{
		"id": 1,
		"name": "홍길동",
		"age": 24,
		"email": "gildong24@example.com",
		"password": "Password1234!!"
	},
	{
		"id": 2,
		"name": "장문복",
		"age": 21,
		"email": "moonluck12@example.com",
		"password": "Check1321!"
	},
	{
		"id": 3,
		"name": "임우진",
		"age": 31,
		"email": "limousine33@example.com",
		"password": "lwsPAssword12@"
	}
]

@router.get("/users")
def get_users():
    return [
        {
            "id": user["id"],
            "name": user["name"],
            "age": user["age"],
            "email": user["email"]
        }
        for user in user_list
    ]

@router.get("/users/{user_id}")
def get_user(user_id: int):
    for user in user_list:
        if user["id"] == user_id:
            return {
                "id": user["id"],
                "name": user["name"],
                "age": user["age"],
                "email": user["email"]
            }

    raise HTTPException(
        status_code=404,
        detail="해당 회원을 찾을 수 없습니다."
    )

@router.post("/users")
def create_user(user: UserCreate):
    new_id = max(member["id"] for member in user_list) + 1

    new_user = {
        "id": new_id,
        "name": user.name,
        "age": user.age,
        "email": user.email,
        "password": user.password
    }

    user_list.append(new_user)

    return {
        "id": new_user["id"],
        "name": new_user["name"],
        "age": new_user["age"],
        "email": new_user["email"]
    }

@router.patch("/users/{user_id}")
def update_user(user_id: int, update_data: UserUpdate):
    for user in user_list:
        if user["id"] == user_id:

            if update_data.name is not None:
                user["name"] = update_data.name

            if update_data.age is not None:
                user["age"] = update_data.age

            if update_data.email is not None:
                user["email"] = update_data.email

            if update_data.password is not None:
                user["password"] = update_data.password

            return {
                "id": user["id"],
                "name": user["name"],
                "age": user["age"],
                "email": user["email"]
            }

    raise HTTPException(
        status_code=404,
        detail="해당 회원을 찾을 수 없습니다."
    )

@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    for user in user_list:
        if user["id"] == user_id:
            user_list.remove(user)

            return {
                "message": "회원이 성공적으로 삭제되었습니다."
            }

    raise HTTPException(
        status_code=404,
        detail="해당 회원을 찾을 수 없습니다."
    )