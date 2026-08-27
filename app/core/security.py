"""비밀번호 해싱과 Bearer JWT 처리 함수입니다."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """별도 로그인 API에서 사용할 HS256 JWT를 생성합니다."""
    expires_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "exp": int((datetime.now(UTC) + expires_delta).timestamp()),
    }
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(settings.JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """JWT 서명과 만료 시간을 검증합니다."""
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        expected = hmac.new(
            settings.JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_base64url_decode(encoded_signature), expected):
            return None
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
        if header.get("alg") != "HS256" or not isinstance(payload.get("sub"), str):
            return None
        if int(payload["exp"]) <= int(time.time()):
            return None
        return payload
    except (AttributeError, KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError):
        return None
