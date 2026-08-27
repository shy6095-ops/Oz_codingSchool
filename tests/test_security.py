import jwt

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password


def test_access_payload_has_only_user_id_and_exp():
    token = create_access_token(7)

    payload = jwt.decode(token, settings.ACCESS_TOKEN_SECRET_KEY, algorithms=["HS256"])

    assert set(payload) == {"user_id", "exp"}
    assert payload["user_id"] == 7


async def test_password_hash_round_trip():
    password = "Aa1!secure"

    assert await verify_password(password, await hash_password(password))
