import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_bundle_contains_backend_executable_and_alembic_resources(tmp_path):
    """Catches a build that omits the backend executable or migration resources."""
    dist_dir = tmp_path / "dist"
    work_dir = tmp_path / "work"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--distpath",
                str(dist_dir),
                "--workpath",
                str(work_dir),
                "SellHelpBackend.spec",
            ],
            cwd=BACKEND_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError("PyInstaller bundle did not finish within 180 seconds") from error
    assert completed.returncode == 0, completed.stderr

    bundle_dir = dist_dir / "SellHelpBackend"
    assert (bundle_dir / "SellHelpBackend.exe").is_file()
    assert (bundle_dir / "_internal" / "alembic").is_dir()
    assert (bundle_dir / "_internal" / "alembic.ini").is_file()
