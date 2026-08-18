import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_backend_test_fixture_imports_without_framework_warnings():
    result = subprocess.run(
        [sys.executable, "-W", "error", "-c", "import runpy; runpy.run_path('tests/conftest.py')"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
