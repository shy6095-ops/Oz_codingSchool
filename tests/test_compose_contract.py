import json
import os
import subprocess
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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

        bind_mounts = [
            volume for volume in fastapi["volumes"] if volume["type"] == "bind"
        ]
        self.assertEqual(len(bind_mounts), 1)
        self.assertEqual(bind_mounts[0]["source"], str(PROJECT_ROOT))
        self.assertEqual(bind_mounts[0]["target"], "/app")

    def test_dockerignore_excludes_non_runtime_and_sensitive_paths(self) -> None:
        root_ignore = PROJECT_ROOT / ".dockerignore"
        assignment_ignore = PROJECT_ROOT / "app" / ".dockerignore"

        self.assertTrue(root_ignore.is_file())
        self.assertTrue(assignment_ignore.is_file())
        self.assertEqual(root_ignore.read_text(), assignment_ignore.read_text())

        patterns = {
            line.strip()
            for line in root_ignore.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for required_pattern in {
            ".env*",
            "**/__pycache__/",
            ".mypy_cache/",
            "Dockerfile*",
            "docker-compose*.yml",
            "docs/",
            "README*",
            ".idea/",
            ".vscode/",
        }:
            self.assertIn(required_pattern, patterns)

    def test_python_package_metadata_only_references_build_context_files(self) -> None:
        pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())

        for package in pyproject["tool"]["setuptools"]["packages"]:
            package_directory = PROJECT_ROOT.joinpath(*package.split("."))
            self.assertTrue(
                package_directory.is_dir(),
                f"declared package directory is missing: {package}",
            )

        self.assertNotIn("readme", pyproject["project"])
