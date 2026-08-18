import argparse
import os
from pathlib import Path
from typing import Sequence


def is_desktop_mode() -> bool:
    return os.getenv("SELLHELP_DESKTOP_MODE") == "1"


def desktop_data_dir() -> Path:
    configured_path = os.getenv("SELLHELP_DATA_DIR") if is_desktop_mode() else None
    if configured_path:
        return Path(configured_path)
    return Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SellHelp"


def desktop_static_dir() -> Path | None:
    configured_path = os.getenv("SELLHELP_STATIC_DIR") if is_desktop_mode() else None
    return Path(configured_path) if configured_path else None


def parse_desktop_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=desktop_data_dir())
    parser.add_argument("--static-dir", type=Path)
    parser.add_argument("--port", type=int, default=8001)
    return parser.parse_args(argv)
