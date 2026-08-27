from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def login(self, payload: LoginRequest) -> tuple[User, str, str]:
        user = await self.repository.get_active_by_email(str(payload.email))
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 일치하지 않습니다.")
        access_token, refresh_token, refresh_jti, refresh_expires_at = self._issue_tokens(user.id)
        await self.repository.create_refresh_token(user.id, refresh_jti, refresh_expires_at)
        await self.repository.db.commit()
        return user, access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token, "refresh")
        if payload is None or not isinstance(payload.get("jti"), str):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 유효하지 않습니다.")
        user = await self.repository.get_active_by_id(int(payload["sub"]))
        stored_token = await self.repository.get_valid_refresh_token(payload["jti"], user.id) if user else None
        if stored_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰이 유효하지 않습니다.")
        stored_token.revoked = True
        access_token, new_refresh_token, new_jti, expires_at = self._issue_tokens(user.id)
        await self.repository.create_refresh_token(user.id, new_jti, expires_at)
        await self.repository.db.commit()
        return access_token, new_refresh_token

    async def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            payload = decode_token(refresh_token, "refresh")
            if payload and isinstance(payload.get("jti"), str):
                await self.repository.revoke_refresh_token(payload["jti"])
                await self.repository.db.commit()

    @staticmethod
    def _issue_tokens(user_id: int):
        refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(user_id)
        return create_access_token(user_id), refresh_token, refresh_jti, refresh_expires_at
