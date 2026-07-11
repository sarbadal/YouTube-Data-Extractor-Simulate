from __future__ import annotations

from youtube_extractor.models import ExtractionConfig
from youtube_extractor.utils import date_window, parse_date


def _resolve_status_value(row: dict[str, str]) -> str:
    for key in ("campaign_status", "adgroup_status", "ad_status"):
        value = row.get(key)
        if value:
            return value
    return ""


def filter_rows(rows: list[dict[str, str]], config: ExtractionConfig) -> list[dict[str, str]]:
    start, end = date_window(config.date_range)
    allowed_status = set(config.filters.get("campaign_status", []))
    allowed_campaign_ids = set(config.filters.get("campaign_ids", []))

    filtered: list[dict[str, str]] = []
    for row in rows:
        if row.get("client_id") != config.client_id:
            continue

        row_date_raw = row.get("date")
        if row_date_raw and (start or end):
            row_date = parse_date(row_date_raw)
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue

        status_value = _resolve_status_value(row)
        if allowed_status and status_value not in allowed_status:
            continue

        if allowed_campaign_ids and row.get("campaign_id") not in allowed_campaign_ids:
            continue

        filtered.append(row)

    return filtered


def project_columns(rows: list[dict[str, str]], columns: list[str]) -> list[dict[str, str]]:
    if not rows:
        return rows
    if not columns:
        return rows

    return [{col: row.get(col, "") for col in columns} for row in rows]
