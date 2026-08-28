"""Runtime paths shared by source, installed, and portable distributions."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent
FROZEN = bool(getattr(sys, "frozen", False))
BINARY_ROOT = Path(sys.executable).resolve().parent if FROZEN else SOURCE_ROOT
ASSET_ROOT = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT)).resolve()


def _default_data_root() -> Path:
    override = os.environ.get("FLOWWORKLIST_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if (BINARY_ROOT / "portable.mode").exists() or os.environ.get("FLOWWORKLIST_PORTABLE") == "1":
        return BINARY_ROOT / "data"

    if not FROZEN:
        return SOURCE_ROOT

    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", BINARY_ROOT)) / "FlowWorklist"

    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg_data:
        return Path(xdg_data).expanduser() / "flowworklist"
    return Path.home() / ".local" / "share" / "flowworklist"


DATA_ROOT = _default_data_root()


def ensure_data_layout() -> Path:
    """Create writable runtime directories and a blank first-run config."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ("logs", "service_logs", "mpps-actions", "dicom-printer"):
        (DATA_ROOT / name).mkdir(parents=True, exist_ok=True)

    config_path = DATA_ROOT / "config.json"
    if not config_path.exists():
        template = ASSET_ROOT / "config.initial.json"
        if not template.exists():
            template = SOURCE_ROOT / "config.initial.json"
        if template.exists():
            shutil.copyfile(template, config_path)
    return DATA_ROOT


def bundled_executable(name: str) -> Path | None:
    """Return a packaged companion executable when one exists."""
    suffix = ".exe" if os.name == "nt" else ""
    candidate = BINARY_ROOT / f"{name}{suffix}"
    return candidate if candidate.exists() else None
