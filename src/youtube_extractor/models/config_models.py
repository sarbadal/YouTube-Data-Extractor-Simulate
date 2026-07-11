from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExtractionConfig:
    platform: str
    dataset: str
    client_id: str
    date_range: dict[str, Any]
    filters: dict[str, Any]
    select_columns: list[str]
    output: dict[str, str]


def load_config(config_path: str | Path) -> ExtractionConfig:
    path = Path(config_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    return ExtractionConfig(
        platform=payload["platform"],
        dataset=payload["dataset"],
        client_id=payload["client_id"],
        date_range=payload.get("date_range", {}),
        filters=payload.get("filters", {}),
        select_columns=payload.get("select_columns", []),
        output=payload.get("output", {"path": "outputs/extraction.csv"}),
    )
