import importlib
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class PatientApiContractTests(unittest.TestCase):
    def test_patient_api_router_exposes_required_routes(self) -> None:
        """환자 및 진료기록 요구사항의 API 라우트가 제공되어야 한다."""
        module = importlib.import_module("app.apis.patient_apis")
        routes = {(route.path, tuple(route.methods or ())) for route in module.router.routes}

        self.assertIn(("/api/v1/patients", ("POST",)), routes)
        self.assertIn(("/api/v1/patients", ("GET",)), routes)
        self.assertIn(("/api/v1/patients/{patient_id}", ("GET",)), routes)
        self.assertIn(("/api/v1/patients/{patient_id}", ("PATCH",)), routes)
        self.assertIn(("/api/v1/patients/{patient_id}", ("DELETE",)), routes)
        self.assertIn(("/api/v1/patients/{patient_id}/medical-records", ("GET",)), routes)
        self.assertIn(("/api/v1/medical-records", ("POST",)), routes)
        self.assertIn(("/api/v1/medical-records/{record_id}", ("GET",)), routes)

    def test_patient_record_and_xray_are_created_then_deleted_together(self) -> None:
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            patient_response = client.post(
                "/api/v1/patients",
                json={
                    "name": "홍길동",
                    "age": 45,
                    "gender": "M",
                    "phone_number": "01012345678",
                },
            )
            self.assertEqual(patient_response.status_code, 201)
            patient = patient_response.json()

            listed = client.get("/api/v1/patients?name=홍&gender=M&min_age=40&max_age=50")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual([item["id"] for item in listed.json()], [patient["id"]])

            updated = client.patch(
                f"/api/v1/patients/{patient['id']}",
                json={"phone_number": "01099998888"},
            )
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()["phone_number"], "01099998888")

            record_response = client.post(
                "/api/v1/medical-records",
                data={
                    "patient_id": str(patient["id"]),
                    "chart_number": "CH-001",
                    "symptoms": "기침과 발열",
                },
                files={"xray_image": ("xray.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )
            self.assertEqual(record_response.status_code, 201)
            record = record_response.json()
            image_path = Path("media") / "xrays" / Path(record["xray_image_url"]).name
            self.assertTrue(image_path.exists())

            deleted = client.delete(f"/api/v1/patients/{patient['id']}")
            self.assertEqual(deleted.status_code, 204)
            self.assertFalse(image_path.exists())
            self.assertEqual(client.get(f"/api/v1/patients/{patient['id']}").status_code, 404)
            self.assertEqual(client.get(f"/api/v1/medical-records/{record['id']}").status_code, 404)

    def test_medical_record_can_be_created_without_an_xray_image(self) -> None:
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            patient_response = client.post(
                "/api/v1/patients",
                json={
                    "name": "김영희",
                    "age": 38,
                    "gender": "F",
                    "phone_number": "01022223333",
                },
            )
            self.assertEqual(patient_response.status_code, 201)
            patient_id = patient_response.json()["id"]

            record_response = client.post(
                "/api/v1/medical-records",
                data={
                    "patient_id": str(patient_id),
                    "chart_number": "CH-002",
                    "symptoms": "두통",
                },
            )
            self.assertEqual(record_response.status_code, 201)
            record = record_response.json()
            self.assertIsNone(record["xray_image_url"])

            detail = client.get(f"/api/v1/medical-records/{record['id']}")
            self.assertEqual(detail.status_code, 200)
            self.assertIsNone(detail.json()["xray_image_url"])
            self.assertEqual(client.delete(f"/api/v1/patients/{patient_id}").status_code, 204)


if __name__ == "__main__":
    unittest.main()
