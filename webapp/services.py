from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from .constants import CONFIG_OUTPUT_DIR, PROJECT_ROOT, SRC_PATH

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from youtube_extractor.extractors import run_extraction


def save_generated_config(config_payload: dict) -> Path:
    CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config_name = f"config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    config_path = CONFIG_OUTPUT_DIR / config_name
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return config_path


def execute_extraction(config_path: Path) -> Path:
    return run_extraction(config_path=config_path, project_root=PROJECT_ROOT)


def resolve_output_download_path(file_param: str) -> Path:
    target = (PROJECT_ROOT / file_param).resolve()
    outputs_root = (PROJECT_ROOT / "outputs").resolve()

    if not str(target).startswith(str(outputs_root)):
        raise ValueError("Invalid download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested file does not exist")

    return target
