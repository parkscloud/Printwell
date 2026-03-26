r"""Manage %APPDATA%\Printwell directory structure."""

import os
from pathlib import Path

from printwell.constants import APP_NAME


def get_appdata_dir() -> Path:
    """Return the Printwell directory under %APPDATA%, creating it if needed."""
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    """Return path to the config JSON file."""
    return get_appdata_dir() / "config.json"


def get_log_dir() -> Path:
    """Return path to the logs directory."""
    log_dir = get_appdata_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
