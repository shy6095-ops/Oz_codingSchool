import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.bootstrap import ensure_test_user
from app.core.config import settings
from app.core.db.databases import Base, async_get_db
from app.core.security import verify_password
from app.main import app
from app.worker.models.user import Department, Role, User


class UserWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_secret_key = settings.SECRET_KEY
        cls.original_secure_cookies = settings.SECURE_COOKIES
        settings.SECRET_KEY = "test-only-secret-key-with-at-least-32-characters"
        settings.SECURE_COOKIES = False

        file_descriptor, cls.database_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_path}")
        cls.session_factory = async_sessionmaker(cls.engine, expire_on_commit=False)
        asyncio.run(cls._create_schema())

        async def override_get_db():
            async with cls.session_factory() as session:
                yield session

        app.dependency_overrides[async_get_db] = override_get_db

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        settings.SECRET_KEY = cls.original_secret_key
        settings.SECURE_COOKIES = cls.original_secure_cookies
        asyncio.run(cls.engine.dispose())
        Path(cls.database_path).unlink(missing_ok=True)

    @classmethod
    async def _create_schema(cls) -> None:
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def _ensure_test_account(self) -> User:
        async with self.session_factory() as session:
            return await ensure_test_user(
                session,
                enabled=True,
                email="bootstrap@example.com",
                password="2468",
                name="테스트 사용자",
                phone_number="01000000000",
            )

    def test_bootstrap_account_can_login_refresh_and_continue_to_me(self) -> None:
        user = asyncio.run(self._ensure_test_account())

        self.assertEqual(user.email, "bootstrap@example.com")
        self.assertEqual(user.role, Role.STAFF)
        self.assertEqual(user.department, Department.MEDICAL)
        self.assertTrue(verify_password("2468", user.hashed_password))

        with TestClient(app, raise_server_exceptions=False) as client:
            login = client.post(
                "/api/v1/users/login",
                json={"email": "bootstrap@example.com", "password": "2468"},
            )
            self.assertEqual(login.status_code, 200)
            self.assertNotIn("Secure", login.headers["set-cookie"])

            access_token = login.json()["access_token"]
            me = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["email"], "bootstrap@example.com")
            self.assertEqual(me.json()["role"], "STAFF")
            self.assertEqual(me.json()["department"], "MEDICAL")

            refresh = client.post("/api/v1/users/token/refresh")
            self.assertEqual(refresh.status_code, 200)
            self.assertIn("access_token", refresh.json())

    def test_bootstrap_is_idempotent(self) -> None:
        asyncio.run(self._ensure_test_account())
        asyncio.run(self._ensure_test_account())

        async def count_accounts() -> int:
            async with self.session_factory() as session:
                statement = select(func.count()).select_from(User).where(
                    User.email == "bootstrap@example.com"
                )
                return (await session.execute(statement)).scalar_one()

        self.assertEqual(asyncio.run(count_accounts()), 1)

    def test_regular_signup_remains_pending_and_requires_a_strong_password(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            weak_signup = client.post(
                "/api/v1/users/signup",
                json={
                    "email": "weak@example.com",
                    "password": "short",
                    "name": "약한 비밀번호",
                    "department": "DEV",
                    "gender": "M",
                    "phone_number": "01011110000",
                },
            )
            self.assertEqual(weak_signup.status_code, 422)

            signup = client.post(
                "/api/v1/users/signup",
                json={
                    "email": "pending@example.com",
                    "password": "Strong1234!",
                    "name": "승인 대기",
                    "department": "RESEARCH",
                    "gender": "F",
                    "phone_number": "01022220000",
                },
            )
            self.assertEqual(signup.status_code, 201)
            self.assertEqual(signup.json()["role"], "PENDING")
