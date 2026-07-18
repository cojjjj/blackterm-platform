from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
import json
import os


APP_DIR = Path.home() / ".blackterm-recon"
DEFAULT_CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_DB_PATH = APP_DIR / "history.db"
DEFAULT_LOG_PATH = APP_DIR / "blackterm.log"
DEFAULT_PLUGIN_DIR = APP_DIR / "plugins"


@dataclass(slots=True)
class AppConfig:
    timeout: float = 0.5
    workers: int = 100
    banners: bool = False
    banner_timeout: float = 0.7
    log_level: str = "INFO"
    database_path: str = str(DEFAULT_DB_PATH)
    log_path: str = str(DEFAULT_LOG_PATH)
    plugin_directory: str = str(DEFAULT_PLUGIN_DIR)
    allow_public_targets: bool = False
    theme: str = "Purple Void"

    def validate(self) -> None:
        if not 0.05 <= self.timeout <= 30:
            raise ValueError("timeout must be between 0.05 and 30 seconds")
        if not 1 <= self.workers <= 1000:
            raise ValueError("workers must be between 1 and 1000")
        if not 0.05 <= self.banner_timeout <= 30:
            raise ValueError("banner_timeout must be between 0.05 and 30 seconds")
        self.log_level = self.log_level.upper()

    def to_dict(self) -> dict:
        return asdict(self)


_ENV_MAP = {
    "BLACKTERM_TIMEOUT": ("timeout", float),
    "BLACKTERM_WORKERS": ("workers", int),
    "BLACKTERM_BANNERS": ("banners", lambda v: v.lower() in {"1", "true", "yes", "on"}),
    "BLACKTERM_LOG_LEVEL": ("log_level", str),
}


def ensure_dirs(config: AppConfig) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    Path(config.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    Path(config.log_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    Path(config.plugin_directory).expanduser().mkdir(parents=True, exist_ok=True)


def save_config(config: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    config.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return path


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    valid = {f.name for f in fields(AppConfig)}
    data = {}
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        data.update({k: v for k, v in raw.items() if k in valid})

    for env_name, (field_name, converter) in _ENV_MAP.items():
        if env_name in os.environ:
            data[field_name] = converter(os.environ[env_name])

    config = AppConfig(**data)
    config.validate()
    ensure_dirs(config)
    if not path.exists():
        save_config(config, path)
    return config
