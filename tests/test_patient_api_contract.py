import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.databases import Base, async_get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.worker.models.user import Department, Gender, Role, User


class PatientApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_secret_key = settings.SECRET_KEY
        settings.SECRET_KEY = "test-only-secret-key-with-at-least-32-characters"
        file_descriptor, cls.database_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_path}")
        cls.session_factory = async_sessionmaker(cls.engine, expire_on_commit=False)
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

    @classmethod
    async def _create_schema_and_users(cls) -> None:
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with cls.session_factory() as session:
            medical_user = User(
                email="medical@example.com",
                hashed_password="not-used-in-this-test",
                name="의료인",
                department=Department.MEDICAL,
                gender=Gender.F,
                phone_number="01011112222",
                role=Role.STAFF,
                is_active=True,
            )
            developer_user = User(
                email="developer@example.com",
                hashed_password="not-used-in-this-test",
                name="개발자",
                department=Department.DEV,
                gender=Gender.M,
                phone_number="01033334444",
                role=Role.STAFF,
                is_active=True,
            )
            session.add_all([medical_user, developer_user])
            await session.commit()
            cls.medical_headers = {
                "Authorization": f"Bearer {create_access_token(medical_user.id)}"
            }
            cls.developer_headers = {
                "Authorization": f"Bearer {create_access_token(developer_user.id)}"
            }

    def test_patient_list_requires_an_access_token(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/patients")

        self.assertEqual(response.status_code, 401)

    def test_non_medical_user_cannot_register_a_patient(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/patients",
                headers=self.developer_headers,
                json={
                    "name": "홍길동",
                    "age": 45,
                    "gender": "M",
                    "phone_number": "01012345678",
                },
            )

        self.assertEqual(response.status_code, 403)

    def test_medical_user_can_create_paginate_and_delete_patient_records(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            patient_response = client.post(
                "/api/v1/patients",
                headers=self.medical_headers,
                json={
                    "name": "김영희",
                    "age": 38,
                    "gender": "F",
                    "phone_number": "01022223333",
                },
            )
            self.assertEqual(patient_response.status_code, 201)
            patient_id = patient_response.json()["id"]

            patients = client.get(
                "/api/v1/patients?page=1&size=10",
                headers=self.medical_headers,
            )
            self.assertEqual(patients.status_code, 200)
            self.assertGreaterEqual(patients.json()["total"], 1)
            self.assertEqual(patients.json()["page"], 1)

            record_response = client.post(
                f"/api/v1/patients/{patient_id}/medical-records",
                headers=self.medical_headers,
                data={"chart_number": "CH-002", "symptoms": "두통"},
            )
            self.assertEqual(record_response.status_code, 201)
            record = record_response.json()
            self.assertIsNone(record["xray_image_url"])

            records = client.get(
                f"/api/v1/patients/{patient_id}/medical-records?page=1&size=10",
                headers=self.medical_headers,
            )
            self.assertEqual(records.status_code, 200)
            self.assertEqual(records.json()["total"], 1)

            detail = client.get(
                f"/api/v1/patients/{patient_id}/medical-records/{record['id']}",
                headers=self.medical_headers,
            )
            self.assertEqual(detail.status_code, 200)
            self.assertIsNone(detail.json()["xray_image_url"])

            deleted = client.delete(
                f"/api/v1/patients/{patient_id}", headers=self.medical_headers
            )
            self.assertEqual(deleted.status_code, 204)

    def test_uploaded_xray_is_deleted_with_its_patient(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            patient_response = client.post(
                "/api/v1/patients",
                headers=self.medical_headers,
                json={
                    "name": "이철수",
                    "age": 50,
                    "gender": "M",
                    "phone_number": "01055556666",
                },
            )
            patient_id = patient_response.json()["id"]
            record_response = client.post(
                f"/api/v1/patients/{patient_id}/medical-records",
                headers=self.medical_headers,
                data={"chart_number": "CH-003", "symptoms": "기침"},
                files={"xray_image": ("xray.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )
            self.assertEqual(record_response.status_code, 201)
            image_path = Path("media") / "xrays" / Path(
                record_response.json()["xray_image_url"]
            ).name
            self.assertTrue(image_path.exists())

            self.assertEqual(
                client.delete(
                    f"/api/v1/patients/{patient_id}", headers=self.medical_headers
                ).status_code,
                204,
            )
            self.assertFalse(image_path.exists())
