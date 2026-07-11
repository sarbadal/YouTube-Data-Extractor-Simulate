from __future__ import annotations

from datetime import datetime
from typing import Any

from .constants import DATASET_DEFAULT_COLUMNS, DATASET_OPTIONS


def as_list(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_relative_date_range(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "relative",
        "last_n_days": int(form.get("last_n_days", "7")),
        "anchor_date": form.get("anchor_date", "").strip(),
    }


def _build_explicit_date_range(form: dict[str, Any]) -> dict[str, Any]:
    start_date = form.get("start_date", "").strip()
    end_date = form.get("end_date", "").strip()
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required for explicit mode")

    return {
        "mode": "explicit",
        "start_date": start_date,
        "end_date": end_date,
    }


DATE_RANGE_BUILDERS = {
    "relative": _build_relative_date_range,
    "explicit": _build_explicit_date_range,
}


def _resolve_columns_from_input(selected_columns_raw: str, dataset: str) -> list[str]:
    strategies = {
        "custom": lambda: as_list(selected_columns_raw),
        "default": lambda: DATASET_DEFAULT_COLUMNS[dataset],
    }
    strategy_key = "custom" if selected_columns_raw else "default"
    return strategies[strategy_key]()


def build_config(form: dict[str, Any], selected_status: list[str]) -> dict[str, Any]:
    client_id = form.get("client_id", "").strip()
    dataset = form.get("dataset", "campaign_daily").strip()
    date_mode = form.get("date_mode", "relative").strip()

    if not client_id:
        raise ValueError("client_id is required")
    if dataset not in DATASET_OPTIONS:
        raise ValueError("Unsupported dataset selected")

    date_range_builder = DATE_RANGE_BUILDERS.get(date_mode)
    if not date_range_builder:
        raise ValueError("Invalid date mode")
    date_range = date_range_builder(form)

    campaign_ids = as_list(form.get("campaign_ids", ""))

    selected_columns_raw = form.get("select_columns", "").strip()
    select_columns = _resolve_columns_from_input(selected_columns_raw, dataset)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/report_{client_id}_{dataset}_{timestamp}.csv"

    return {
        "platform": "youtube",
        "dataset": dataset,
        "client_id": client_id,
        "date_range": date_range,
        "filters": {
            "campaign_status": selected_status,
            "campaign_ids": campaign_ids,
        },
        "select_columns": select_columns,
        "output": {
            "path": output_path,
        },
    }
