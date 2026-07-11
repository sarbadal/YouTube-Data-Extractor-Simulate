from __future__ import annotations

from youtube_extractor.models import ExtractionConfig
from youtube_extractor.utils import date_window, parse_date


def _resolve_status_value(row: dict[str, str]) -> str:
    """Extract a normalized status value from a row across supported schemas.

    Different template datasets store status in different columns
    (for example ``campaign_status``, ``adgroup_status``, or ``ad_status``).
    This helper checks known status keys in priority order and returns the
    first non-empty value.

    Args:
        row: A single extracted data row represented as a string dictionary.

    Returns:
        The first available non-empty status value, or an empty string when no
        known status column is present.
    """
    for key in ("campaign_status", "adgroup_status", "ad_status"):
        value = row.get(key)
        if value:
            return value
    return ""


def filter_rows(rows: list[dict[str, str]], config: ExtractionConfig) -> list[dict[str, str]]:
    """Apply client/date/status/campaign filters to raw template rows.

    This function is the core filtering stage for all dataset types. It keeps
    only rows that match the requested client, optional date window,
    optional status list, and optional campaign id list.

    Filtering behavior:
    - ``client_id`` is always required and enforced.
    - Date filtering is applied only when ``date_range`` resolves to a window.
    - Status filtering is applied only when statuses are provided.
    - Campaign id filtering is applied only when ids are provided.

    Args:
        rows: Raw rows loaded from a template CSV.
        config: Parsed extraction configuration containing filters and date
            range information.

    Returns:
        A new list containing only rows that satisfy all active filter rules.
    """
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
    """Project filtered rows to selected output columns.

    When ``columns`` is provided, each output row includes only those keys,
    preserving column order. Missing keys are emitted as empty strings, which
    keeps CSV output shape stable even when schemas differ by dataset.

    Args:
        rows: Filtered rows to project.
        columns: Target output columns. If empty, rows are returned unchanged.

    Returns:
        Rows containing only requested columns, or original rows when no
        projection is required.
    """
    if not rows:
        return rows
    if not columns:
        return rows

    return [{col: row.get(col, "") for col in columns} for row in rows]
