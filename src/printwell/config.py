"""Application configuration: dataclass + JSON persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from printwell.utils.paths import get_config_path

log = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Persistent application settings."""

    # Last-used directory for the file browser
    last_open_dir: str = ""


class ConfigManager:
    """Load and save AppConfig to JSON in %APPDATA%\\Printwell."""

    def __init__(self, path: Path | None = None):
        self.path = path or get_config_path()
        self.config = self._load()

    def _load(self) -> AppConfig:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return AppConfig(**{
                    k: v for k, v in data.items()
                    if k in AppConfig.__dataclass_fields__
                })
            except Exception:
                log.warning("Failed to load config, using defaults", exc_info=True)
        return AppConfig()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(self.config), indent=2),
            encoding="utf-8",
        )
        log.debug("Config saved to %s", self.path)
