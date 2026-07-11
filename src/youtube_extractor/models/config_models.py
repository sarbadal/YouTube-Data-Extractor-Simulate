from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExtractionConfig:
    """Normalized extraction configuration used by the simulator pipeline."""

    platform: str
    dataset: str
    client_id: str
    date_range: dict[str, Any]
    filters: dict[str, Any]
    select_columns: list[str]
    output: dict[str, str]


def load_config(config_path: str | Path) -> ExtractionConfig:
    """Load and normalize an extraction config JSON into ``ExtractionConfig``.

    This function reads the provided JSON config file, validates required fields
    by direct key access (which raises when missing), and applies safe defaults
    for optional sections. The returned dataclass is the single config object
    used by the extractor flow.

    Required JSON keys:
    - ``platform``
    - ``dataset``
    - ``client_id``

    Optional JSON keys (defaults applied when missing):
    - ``date_range`` -> ``{}``
    - ``filters`` -> ``{}``
    - ``select_columns`` -> ``[]``
    - ``output`` -> ``{"path": "outputs/extraction.csv"}``

    Args:
        config_path: Path to a JSON config file.

    Returns:
        A populated ``ExtractionConfig`` instance.

    Raises:
        FileNotFoundError: If ``config_path`` does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required keys are missing from the JSON payload.
    """
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
