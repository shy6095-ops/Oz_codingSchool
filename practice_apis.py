import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator


router = APIRouter()


class UserCreate(BaseModel):
	name: str = Field(min_length=2, max_length=10)
	age: int = Field(ge=14)
	email: str = Field(max_length=30)
	password: str = Field(min_length=8, max_length=20)

	@model_validator(mode="after")
	def validate_user(self):
		validate_email(self.email)
		validate_password(self.password)
		return self


class UserUpdate(BaseModel):
	name: str | None = Field(default=None, min_length=2, max_length=10)
	age: int | None = Field(default=None, ge=14)
	email: str | None = Field(default=None, max_length=30)
	password: str | None = Field(default=None, min_length=8, max_length=20)

	@model_validator(mode="after")
	def validate_update(self):
		if self.email is not None:
			validate_email(self.email)
		if self.password is not None:
			validate_password(self.password)
		return self


def validate_email(email: str):
	if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
		raise ValueError("올바른 이메일 형식이 아닙니다.")


def validate_password(password: str):
	if not re.fullmatch(r"(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).*", password):
		raise ValueError("비밀번호는 대문자, 소문자, 특수문자를 각각 하나 이상 포함해야 합니다.")


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
	if any(existing_user["email"] == user.email for existing_user in user_list):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 이메일입니다.")

	new_user = user.model_dump()
	new_user["id"] = max(existing_user["id"] for existing_user in user_list) + 1
	user_list.append(new_user)
	return new_user


@router.patch("/{user_id}", response_model=dict)
async def update_user(user_id: int, user_update: UserUpdate):
	for user in user_list:
		if user["id"] == user_id:
			changes = user_update.model_dump(exclude_unset=True)
			if not changes or any(value is None for value in changes.values()):
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail="수정할 항목을 하나 이상 입력해야 합니다.",
				)
			if "email" in changes and any(
				existing_user["id"] != user_id and existing_user["email"] == changes["email"]
				for existing_user in user_list
			):
				raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 이메일입니다.")
			user.update(changes)
			return user

	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")


@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: int):
	for index, user in enumerate(user_list):
		if user["id"] == user_id:
			return user_list.pop(index)

	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원을 찾을 수 없습니다.")
