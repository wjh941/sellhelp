from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_configuration_uses_8001_for_the_backend():
    vite_config = (PROJECT_ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
    start_script = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    main_module = (PROJECT_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    init_module = (PROJECT_ROOT / "backend" / "app" / "init_data.py").read_text(encoding="utf-8")

    assert "process.env.VITE_API_PROXY_TARGET || 'http://localhost:8001'" in vite_config
    assert "target: apiProxyTarget" in vite_config
    assert "--port 8001" in start_script
    assert "http://localhost:8001/docs" in start_script
    assert "http://localhost:8001/docs" in readme
    assert "port=8001" in main_module
    assert "--port 8001" in init_module
    assert "http://localhost:8080" in init_module
