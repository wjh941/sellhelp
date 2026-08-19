from pathlib import Path


def test_ci_installs_pinned_backend_test_requirements():
    workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    requirements = Path(__file__).parents[1] / "requirements-test.txt"

    assert "pip install -r backend/requirements-test.txt" in workflow
    assert "pytest==" in requirements.read_text(encoding="utf-8")
