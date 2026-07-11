from __future__ import annotations

import csv
from pathlib import Path


def load_rows(data_path: Path) -> list[dict[str, str]]:
    with data_path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_output(rows: list[dict[str, str]], output_path: Path, fallback_columns: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else fallback_columns

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
