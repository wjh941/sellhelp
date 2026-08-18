import os
from pathlib import Path

from starlette.testclient import TestClient

from app.database import sqlite_database_path
from app.desktop_runtime import (
    desktop_data_dir,
    desktop_static_dir,
    is_desktop_mode,
    parse_desktop_args,
)
from app.main import create_app


def test_desktop_runtime_uses_configured_data_directory(monkeypatch, tmp_path):
    data_dir = tmp_path / "SellHelp"
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    monkeypatch.setenv("SELLHELP_DATA_DIR", str(data_dir))

    assert desktop_data_dir() == data_dir
    assert sqlite_database_path() == data_dir / "data" / "sellhelp.db"


def test_desktop_runtime_ignores_desktop_environment_without_explicit_mode(monkeypatch, tmp_path):
    monkeypatch.delenv("SELLHELP_DESKTOP_MODE", raising=False)
    monkeypatch.setenv("SELLHELP_DATA_DIR", str(tmp_path / "unexpected-data"))
    monkeypatch.setenv("SELLHELP_STATIC_DIR", str(tmp_path / "unexpected-static"))

    assert is_desktop_mode() is False
    assert desktop_static_dir() is None
    assert sqlite_database_path().name == "yingtai.db"


def test_desktop_argument_parser_uses_explicit_values_and_localappdata_default(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    defaults = parse_desktop_args([])
    configured = parse_desktop_args(
        ["--data-dir", "C:/SellHelp", "--static-dir", "C:/SellHelp/dist", "--port", "18101"]
    )

    assert defaults.data_dir == tmp_path / "SellHelp"
    assert defaults.static_dir is None
    assert defaults.port == 8001
    assert configured.data_dir == Path("C:/SellHelp")
    assert configured.static_dir == Path("C:/SellHelp/dist")
    assert configured.port == 18101


def test_desktop_app_serves_dist_and_preserves_api_routes(tmp_path):
    (tmp_path / "index.html").write_text("<main>SellHelp</main>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('SellHelp')", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))

    assert client.get("/api/health").status_code == 200
    assert client.get("/products").status_code == 200
    assert client.get("/").text == "<main>SellHelp</main>"
    assert client.get("/assets/app.js").text == "console.log('SellHelp')"
    assert client.get("/unknown-desktop-route").text == "<main>SellHelp</main>"


def test_desktop_app_disables_api_documentation(monkeypatch):
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")

    app = create_app()

    assert app.docs_url is None
    assert app.redoc_url is None


def test_desktop_entrypoint_enables_desktop_mode_and_binds_loopback(monkeypatch):
    from desktop_main import main

    launched = {}
    desktop_environment_names = (
        "SELLHELP_DESKTOP_MODE",
        "SELLHELP_DATA_DIR",
        "SELLHELP_STATIC_DIR",
    )
    original_environment = {name: os.getenv(name) for name in desktop_environment_names}
    for name in desktop_environment_names:
        os.environ.pop(name, None)
    monkeypatch.setattr("desktop_main.uvicorn.run", lambda *args, **kwargs: launched.update(args=args, kwargs=kwargs))

    try:
        main(["--data-dir", "C:/SellHelp", "--static-dir", "C:/SellHelp/dist", "--port", "18101"])

        assert launched == {
            "args": ("app.main:app",),
            "kwargs": {"host": "127.0.0.1", "port": 18101, "reload": False},
        }
        assert os.getenv("SELLHELP_DESKTOP_MODE") == "1"
        assert os.getenv("SELLHELP_DATA_DIR") == "C:\\SellHelp"
        assert os.getenv("SELLHELP_STATIC_DIR") == "C:\\SellHelp\\dist"
    finally:
        for name, value in original_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
