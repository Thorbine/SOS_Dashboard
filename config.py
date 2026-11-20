"""Konfiguration pro Rechner (nicht im Sync-Ordner): merkt sich den Datenordner.

Unter Windows liegt sie in %APPDATA%\\SOS-Dashboard\\config.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import platform_utils

APP_NAME = "SOS-Dashboard"
CONFIG_FILE = "config.json"


def config_dir() -> Path:
    return platform_utils.config_dir()


def load_config() -> dict:
    try:
        data = json.loads((config_dir() / CONFIG_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    folder = config_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (CONFIG_FILE + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, folder / CONFIG_FILE)


def get_data_dir() -> str | None:
    value = load_config().get("dataDir")
    return value if isinstance(value, str) and value else None


def set_data_dir(path: str) -> None:
    cfg = load_config()
    cfg["dataDir"] = str(path)
    save_config(cfg)
