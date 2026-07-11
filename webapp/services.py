from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from .constants import CONFIG_OUTPUT_DIR, PROJECT_ROOT, SRC_PATH

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from youtube_extractor.extractors import run_extraction

REPORT_RETENTION_LIMIT = 5


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


def resolve_config_download_path(file_param: str) -> Path:
    target = (PROJECT_ROOT / file_param).resolve()
    configs_root = CONFIG_OUTPUT_DIR.resolve()

    if not str(target).startswith(str(configs_root)):
        raise ValueError("Invalid config download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested config file does not exist")

    return target


def list_reports_for_client(client_id: str) -> list[str]:
    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    matches = sorted(
        outputs_root.glob(f"report_{client_id}_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [path.relative_to(PROJECT_ROOT).as_posix() for path in matches]


def list_all_reports() -> list[Path]:
    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    return sorted(
        outputs_root.glob("report_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def prune_old_reports(max_reports: int = REPORT_RETENTION_LIMIT) -> int:
    """Delete older generated report CSV files and keep only the newest max_reports.

    Returns the number of deleted files.
    """
    if max_reports < 1:
        return 0

    reports = list_all_reports()
    stale_reports = reports[max_reports:]

    deleted = 0
    for path in stale_reports:
        try:
            path.unlink()
            deleted += 1
        except OSError:
            # Ignore file deletion failures so report generation flow does not fail.
            continue

    return deleted


def list_recent_report_config_pairs(limit: int = 20) -> list[dict[str, str]]:
    recent_reports = list_all_reports()[:limit]
    pairs: list[dict[str, str]] = []

    for report_path in recent_reports:
        report_name = report_path.name
        timestamp_match = re.search(r"_(\d{8}_\d{6})\.csv$", report_name)
        config_rel = ""

        if timestamp_match:
            timestamp_token = timestamp_match.group(1)
            config_matches = sorted(
                CONFIG_OUTPUT_DIR.glob(f"config_{timestamp_token}_*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if config_matches:
                config_rel = config_matches[0].relative_to(PROJECT_ROOT).as_posix()

        pairs.append(
            {
                "report_file": report_path.relative_to(PROJECT_ROOT).as_posix(),
                "report_name": report_name,
                "config_file": config_rel,
                "config_name": Path(config_rel).name if config_rel else "",
            }
        )

    return pairs
