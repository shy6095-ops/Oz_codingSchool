import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


def utcnow() -> datetime:
    return datetime.now(UTC)


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(password_hasher.hash, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(password_hasher.verify, password, hashed_password)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_token(user_id: int, secret_key: str, expires_in_seconds: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": utcnow() + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(
        payload,
        secret_key,
        algorithm="HS256",
        headers={"kid": secrets.token_urlsafe(16)},
    )


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id, settings.ACCESS_TOKEN_SECRET_KEY, settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id, settings.REFRESH_TOKEN_SECRET_KEY, settings.REFRESH_TOKEN_EXPIRE_SECONDS
    )


def decode_access_token(token: str) -> dict:
    return _decode_token(token, settings.ACCESS_TOKEN_SECRET_KEY)


def decode_refresh_token(token: str) -> dict:
    return _decode_token(token, settings.REFRESH_TOKEN_SECRET_KEY)


def _decode_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if set(payload) != {"user_id", "exp"} or not isinstance(payload["user_id"], int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def payload_expiry(payload: dict) -> datetime:
    return datetime.fromtimestamp(payload["exp"], tz=UTC)
