from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


router = APIRouter()


class UserCreate(BaseModel):
	id: int
	name: str
	age: int = Field(ge=0)
	email: str
	password: str


class UserUpdate(BaseModel):
	age: int = Field(ge=0)
	email: str


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


@router.get("", response_model=list[dict])
async def get_users():
	return user_list


@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: int):
	for user in user_list:
		if user["id"] == user_id:
			return user

	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
	if any(existing_user["id"] == user.id for existing_user in user_list):
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 존재하는 회원 ID입니다.")

	new_user = user.model_dump()
	user_list.append(new_user)
	return new_user


@router.patch("/{user_id}", response_model=dict)
async def update_user(user_id: int, user_update: UserUpdate):
	for user in user_list:
		if user["id"] == user_id:
			user.update(user_update.model_dump())
			return user

	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")


@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: int):
	for index, user in enumerate(user_list):
		if user["id"] == user_id:
			return user_list.pop(index)

	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")

