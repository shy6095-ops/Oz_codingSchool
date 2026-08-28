from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


ALGORITHM = "HS256"


def _create_token(
    user_id: int,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_access_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )

def decode_token(
    token: str,
    expected_token_type: str,
) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except InvalidTokenError as error:
        raise ValueError("유효하지 않거나 만료된 토큰입니다.") from error

    if payload.get("type") != expected_token_type:
        raise ValueError("토큰 종류가 올바르지 않습니다.")

    return payload