from pathlib import Path


def test_pull_request_ci_installs_dev_dependencies_and_runs_tests():
    workflow = Path(".github/workflows/test.yml")

    assert workflow.exists()
    contents = workflow.read_text()
    assert "pull_request:" in contents
    assert "main" in contents
    assert "uv sync --group dev" in contents
    assert "uv run pytest -v" in contents
