# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


BACKEND_ROOT = Path(SPECPATH)

a = Analysis(
    [str(BACKEND_ROOT / "desktop_main.py")],
    pathex=[str(BACKEND_ROOT)],
    binaries=[],
    datas=[
        (str(BACKEND_ROOT / "alembic"), "alembic"),
        (str(BACKEND_ROOT / "alembic.ini"), "."),
    ],
    hiddenimports=["app.main"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SellHelpBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SellHelpBackend",
)
