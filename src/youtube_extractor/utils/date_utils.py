from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def parse_date(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%d")


def date_window(date_range: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    mode = date_range.get("mode", "all")
    if mode == "all":
        return None, None

    if mode == "relative":
        last_n_days = int(date_range.get("last_n_days", 7))
        anchor_raw = date_range.get("anchor_date")
        anchor = parse_date(anchor_raw) if anchor_raw else datetime.utcnow()
        start = anchor - timedelta(days=last_n_days - 1)
        return start, anchor

    if mode == "explicit":
        start_raw = date_range.get("start_date")
        end_raw = date_range.get("end_date")
        if not start_raw or not end_raw:
            raise ValueError("Explicit mode requires start_date and end_date")
        return parse_date(start_raw), parse_date(end_raw)

    raise ValueError(f"Unsupported date_range.mode: {mode}")
