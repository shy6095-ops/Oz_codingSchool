from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import Department, Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    PasswordChangeRequest,
    UserSignupRequest,
    UserUpdateRequest,
)


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    # REQ-USER-001 회원가입
    async def signup(self, data: UserSignupRequest) -> User:
        if await self.repository.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 이메일입니다.",
            )
        if await self.repository.get_by_phone_number(data.phone_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 휴대폰 번호입니다.",
            )
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            name=data.name,
            department=data.department,
            gender=data.gender,
            phone_number=data.phone_number,
            role=Role.PENDING,  # REQ-USER-005: 신규 가입자는 대기자
        )
        return await self.repository.create(user)

    # REQ-USER-002 로그인 + NFR-USER-001 JWT 발급
    async def login(self, email: str, password: str) -> tuple[str, str]:
        user = await self.repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비활성화된 계정입니다.",
            )
        return create_access_token(user.id), create_refresh_token(user.id)

    # NFR-USER-001 액세스 토큰 재발급
    async def reissue_access_token(self, user_id: int) -> str:
        user = await self.repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 사용자입니다.",
            )
        return create_access_token(user.id)

    # REQ-USER-004 회원 목록 조회 (Admin)
    async def get_user_list(
        self,
        *,
        search: str | None,
        department: Department | None,
        offset: int,
        limit: int,
    ) -> tuple[int, list[User]]:
        return await self.repository.get_list(
            search=search, department=department, offset=offset, limit=limit
        )

    # REQ-USER-005 회원 권한 변경 (Admin)
    async def change_role(self, target_user_id: int, role: Role) -> User:
        user = await self.repository.get_by_id(target_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="대상 회원을 찾을 수 없습니다.",
            )
        return await self.repository.update_role(user, role)

    # REQ-USER-007 회원 정보 수정 (Partial)
    async def update_me(self, user: User, data: UserUpdateRequest) -> User:
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목이 없습니다.",
            )
        if "phone_number" in fields:
            existing = await self.repository.get_by_phone_number(
                fields["phone_number"]
            )
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="이미 사용 중인 휴대폰 번호입니다.",
                )
        return await self.repository.update(user, **fields)

    # REQ-USER-008 비밀번호 변경
    async def change_password(self, user: User, data: PasswordChangeRequest) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기존 비밀번호가 일치하지 않습니다.",
            )
        await self.repository.update(
            user, hashed_password=hash_password(data.new_password)
        )

    # REQ-USER-009 회원 탈퇴
    async def withdraw(self, user: User) -> None:
        await self.repository.delete(user)
