import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db.databases import Base, async_get_db
from app.core.security import create_access_token
from app.main import app
from app.worker.models.user import Department, Gender, Role, User


class PredictionApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_secret_key = settings.SECRET_KEY
        settings.SECRET_KEY = "test-only-secret-key-with-at-least-32-characters"
        file_descriptor, cls.database_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_path}")
        cls.session_factory = async_sessionmaker(cls.engine, expire_on_commit=False)
        cls.image_paths: list[Path] = []
        asyncio.run(cls._create_schema_and_users())

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
        for image_path in cls.image_paths:
            image_path.unlink(missing_ok=True)

    @classmethod
    async def _create_schema_and_users(cls) -> None:
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with cls.session_factory() as session:
            medical_user = User(
                email="prediction-medical@example.com",
                hashed_password="not-used-in-this-test",
                name="의료인",
                department=Department.MEDICAL,
                gender=Gender.F,
                phone_number="01070000001",
                role=Role.STAFF,
                is_active=True,
            )
            developer_user = User(
                email="prediction-dev@example.com",
                hashed_password="not-used-in-this-test",
                name="개발자",
                department=Department.DEV,
                gender=Gender.M,
                phone_number="01070000002",
                role=Role.STAFF,
                is_active=True,
            )
            pending_user = User(
                email="prediction-pending@example.com",
                hashed_password="not-used-in-this-test",
                name="승인대기",
                department=Department.RESEARCH,
                gender=Gender.F,
                phone_number="01070000003",
                role=Role.PENDING,
                is_active=True,
            )
            session.add_all([medical_user, developer_user, pending_user])
            await session.commit()
            cls.medical_headers = {
                "Authorization": f"Bearer {create_access_token(medical_user.id)}"
            }
            cls.developer_headers = {
                "Authorization": f"Bearer {create_access_token(developer_user.id)}"
            }
            cls.pending_headers = {
                "Authorization": f"Bearer {create_access_token(pending_user.id)}"
            }

    def _create_record(self, client: TestClient, with_xray: bool) -> tuple[int, int]:
        suffix = len(self.image_paths) + 1
        patient = client.post(
            "/api/v1/patients",
            headers=self.medical_headers,
            json={
                "name": f"예측환자{suffix}",
                "age": 50,
                "gender": "M",
                "phone_number": f"0108000{suffix:04d}",
            },
        )
        self.assertEqual(patient.status_code, 201)
        patient_id = patient.json()["id"]
        request_kwargs = {
            "headers": self.medical_headers,
            "data": {"chart_number": f"PRED-{suffix}", "symptoms": "기침과 발열"},
        }
        if with_xray:
            request_kwargs["files"] = {
                "xray_image": ("xray.png", b"\x89PNG\r\n\x1a\n", "image/png")
            }
        record = client.post(
            f"/api/v1/patients/{patient_id}/medical-records",
            **request_kwargs,
        )
        self.assertEqual(record.status_code, 201)
        if record.json()["xray_image_url"]:
            self.image_paths.append(
                Path("media/xrays") / Path(record.json()["xray_image_url"]).name
            )
        return patient_id, record.json()["id"]

    def test_saved_result_is_returned_without_running_the_model_twice(self) -> None:
        calls = 0

        def predictor(image_path: Path) -> tuple[bool, float]:
            nonlocal calls
            calls += 1
            self.assertTrue(image_path.exists())
            return True, 91.25

        with TestClient(app, raise_server_exceptions=False) as client:
            patient_id, record_id = self._create_record(client, with_xray=True)
            with patch("app.apis.prediction_apis.predict_xray", side_effect=predictor):
                first = client.post(
                    f"/api/v1/medical-records/{record_id}/predict",
                    headers=self.developer_headers,
                )
                second = client.post(
                    f"/api/v1/medical-records/{record_id}/predict",
                    headers=self.developer_headers,
                )
                analyses = client.get(
                    f"/api/v1/medical-records/{record_id}/analyses",
                    headers=self.developer_headers,
                )

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(second.json()["id"], first.json()["id"])
            self.assertEqual(calls, 1)
            self.assertEqual(analyses.status_code, 200)
            self.assertEqual(analyses.json(), [first.json()])
            self.assertEqual(
                set(first.json()),
                {
                    "id",
                    "record_id",
                    "is_pneumonia",
                    "confidence",
                    "heatmap_url",
                    "created_at",
                    "ai_model",
                },
            )
            self.assertTrue(first.json()["is_pneumonia"])
            self.assertEqual(first.json()["confidence"], 91.25)
            self.assertIsNone(first.json()["heatmap_url"])
            self.assertEqual(first.json()["ai_model"], "simple-cnn-v1")
            client.delete(f"/api/v1/patients/{patient_id}", headers=self.medical_headers)

    def test_pending_user_cannot_use_prediction_api(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/medical-records/999/analyses",
                headers=self.pending_headers,
            )

        self.assertEqual(response.status_code, 403)

    def test_missing_record_returns_not_found(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/medical-records/999999/predict",
                headers=self.developer_headers,
            )

        self.assertEqual(response.status_code, 404)

    def test_record_without_xray_cannot_be_predicted(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            patient_id, record_id = self._create_record(client, with_xray=False)
            response = client.post(
                f"/api/v1/medical-records/{record_id}/predict",
                headers=self.developer_headers,
            )
            client.delete(f"/api/v1/patients/{patient_id}", headers=self.medical_headers)

        self.assertEqual(response.status_code, 422)

    def test_model_failure_returns_service_unavailable(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            patient_id, record_id = self._create_record(client, with_xray=True)
            with patch(
                "app.apis.prediction_apis.predict_xray",
                side_effect=RuntimeError("model failed"),
            ):
                response = client.post(
                    f"/api/v1/medical-records/{record_id}/predict",
                    headers=self.developer_headers,
                )
            client.delete(f"/api/v1/patients/{patient_id}", headers=self.medical_headers)

        self.assertEqual(response.status_code, 503)
