import json
import os
import subprocess
import unittest


class DockerComposeContractTests(unittest.TestCase):
    def test_fastapi_waits_for_mysql_and_bootstraps_before_starting(self) -> None:
        environment = {
            **os.environ,
            "DB_PORT": "3306",
            "DB_USER": "test-user",
            "DB_PASSWORD": "test-password",
            "DB_ROOT_PASSWORD": "test-root-password",
            "DB_NAME": "test-db",
            "SECRET_KEY": "test-secret-key",
            "SECURE_COOKIES": "false",
            "BOOTSTRAP_TEST_USER_ENABLED": "true",
            "BOOTSTRAP_TEST_USER_EMAIL": "compose@example.com",
            "BOOTSTRAP_TEST_USER_PASSWORD": "2468",
        }
        result = subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        config = json.loads(result.stdout)
        fastapi = config["services"]["fastapi"]

        self.assertEqual(fastapi["environment"]["DB_HOST"], "mysql")
        self.assertEqual(fastapi["environment"]["DB_USER"], "test-user")
        self.assertEqual(
            fastapi["depends_on"]["mysql"]["condition"], "service_healthy"
        )

        command = " ".join(fastapi["entrypoint"])
        migration_index = command.index("alembic upgrade head")
        bootstrap_index = command.index("python -m app.bootstrap")
        server_index = command.index("uvicorn app.main:app")
        self.assertLess(migration_index, bootstrap_index)
        self.assertLess(bootstrap_index, server_index)

        volume_targets = {volume["target"] for volume in fastapi["volumes"]}
        self.assertEqual(
            volume_targets,
            {"/app/app", "/app/static", "/app/media"},
        )
