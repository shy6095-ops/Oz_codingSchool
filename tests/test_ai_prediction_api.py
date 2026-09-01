import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db.databases import Base, async_get_db
from app.core.security import create_access_token
from app.main import app
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Department, Gender, Role, User
from app.models.xray_image import XrayImage


class AiPredictionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_secret_key = settings.SECRET_KEY
        settings.SECRET_KEY = "test-only-secret-key-with-at-least-32-characters"
        descriptor, cls.database_path = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_path}")
        cls.session_factory = async_sessionmaker(cls.engine, expire_on_commit=False)
        cls.image_path = Path("media/xrays/ai-prediction-test.png")
        asyncio.run(cls._create_fixture())

        async def override_get_db():
            async with cls.session_factory() as session:
                yield session

        app.dependency_overrides[async_get_db] = override_get_db

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        settings.SECRET_KEY = cls.original_secret_key
        asyncio.run(cls.engine.dispose())
        Path(cls.database_path).unlink(missing_ok=True)
        cls.image_path.unlink(missing_ok=True)

    @classmethod
    async def _create_fixture(cls) -> None:
        cls.image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("L", (128, 128), color=128).save(cls.image_path)

        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with cls.session_factory() as session:
            user = User(
                email="researcher@example.com",
                hashed_password="not-used-in-this-test",
                name="연구자",
                department=Department.RESEARCH,
                gender=Gender.F,
                phone_number="01099990000",
                role=Role.STAFF,
                is_active=True,
            )
            patient = Patient(name="김환자", age=45, gender=Gender.F, phone="01012345678")
            session.add_all([user, patient])
            await session.flush()

            record = MedicalRecord(
                patient_id=patient.id,
                chart_number="CH-AI-001",
                symptoms="기침",
            )
            session.add(record)
            await session.flush()
            session.add(
                XrayImage(
                    record_id=record.id,
                    uploader_id=user.id,
                    image_url="/media/xrays/ai-prediction-test.png",
                    shooting_datetime=record.created_at,
                )
            )
            await session.commit()
            cls.record_id = record.id
            cls.headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}

    def test_prediction_is_saved_then_reused(self) -> None:
        url = f"/api/v1/medical-records/{self.record_id}/pneumonia-predictions"

        with TestClient(app, raise_server_exceptions=False) as client:
            first = client.post(url, headers=self.headers)
            second = client.post(url, headers=self.headers)
            listed = client.get(url, headers=self.headers)

        self.assertEqual(first.status_code, 200)
        self.assertIsInstance(first.json()["has_pneumonia"], bool)
        self.assertIsInstance(first.json()["confidence"], float)
        self.assertEqual(first.json()["is_cached"], False)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["is_cached"], True)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["total"], 1)
