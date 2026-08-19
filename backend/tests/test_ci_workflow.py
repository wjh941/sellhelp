from pathlib import Path


def test_ci_installs_pinned_backend_test_requirements():
    workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    requirements = Path(__file__).parents[1] / "requirements-test.txt"

    assert "pip install -r backend/requirements-test.txt" in workflow
    requirement_lines = requirements.read_text(encoding="utf-8")
    assert "pytest==8.4.2" in requirement_lines
    assert "httpx2==2.10.0" in requirement_lines


def test_ci_runs_windows_desktop_tests_with_build_dependencies():
    workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    requirements = Path(__file__).parents[1] / "requirements-desktop-test.txt"

    assert "windows-desktop:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "pip install -r backend/requirements-desktop-test.txt" in workflow
    assert "tests/test_desktop_bundle.py" in workflow
    assert "tests/test_desktop_runtime.py" in workflow
    assert "tests/test_desktop_startup.py" in workflow
    assert "-r requirements-build.txt" in requirements.read_text(encoding="utf-8")
    assert "pyinstaller==6.17.0" in (requirements.parent / "requirements-build.txt").read_text(
        encoding="utf-8"
    )
