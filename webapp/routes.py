from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from .constants import DATASET_DEFAULT_COLUMNS, DATASET_OPTIONS, PROJECT_ROOT
from .form_config import build_config
from .services import (
    REPORT_RETENTION_LIMIT,
    execute_extraction,
    list_recent_report_config_pairs,
    prune_old_reports,
    resolve_config_download_path,
    resolve_output_download_path,
    save_generated_config,
)

web = Blueprint("web", __name__)
RECENT_REPORT_LIMIT_OPTIONS = (5, 10, 15, 20, 50)
DEFAULT_RECENT_REPORT_LIMIT = 15


@web.get("/")
def index() -> str:
    return render_template(
        "index.html",
        dataset_options=DATASET_OPTIONS,
        dataset_default_columns=DATASET_DEFAULT_COLUMNS,
        today=datetime.utcnow().date().isoformat(),
        recent_report_limit_options=RECENT_REPORT_LIMIT_OPTIONS,
        default_recent_report_limit=DEFAULT_RECENT_REPORT_LIMIT,
    )


@web.post("/generate")
def generate_report() -> Any:
    requested_limit_raw = request.form.get("recent_reports_limit", str(DEFAULT_RECENT_REPORT_LIMIT))
    try:
        requested_limit = int(requested_limit_raw)
    except ValueError:
        requested_limit = DEFAULT_RECENT_REPORT_LIMIT

    if requested_limit not in RECENT_REPORT_LIMIT_OPTIONS:
        requested_limit = DEFAULT_RECENT_REPORT_LIMIT

    effective_recent_limit = min(requested_limit, REPORT_RETENTION_LIMIT)

    try:
        config_payload = build_config(request.form, request.form.getlist("campaign_status"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.index"))

    config_path = save_generated_config(config_payload)

    try:
        output_path = execute_extraction(config_path)
    except Exception as exc:  # noqa: BLE001
        flash(f"Extraction failed: {exc}", "error")
        return redirect(url_for("web.index"))

    prune_old_reports(max_reports=REPORT_RETENTION_LIMIT)

    output_relpath = output_path.relative_to(PROJECT_ROOT)
    recent_report_config_pairs = list_recent_report_config_pairs(limit=effective_recent_limit)
    return render_template(
        "result.html",
        output_file=output_relpath.as_posix(),
        config_file=config_path.relative_to(PROJECT_ROOT).as_posix(),
        recent_report_config_pairs=recent_report_config_pairs,
        recent_reports_limit=effective_recent_limit,
    )


@web.get("/results")
def results_page() -> Any:
    requested_limit_raw = request.args.get("limit", str(DEFAULT_RECENT_REPORT_LIMIT))
    try:
        requested_limit = int(requested_limit_raw)
    except ValueError:
        requested_limit = DEFAULT_RECENT_REPORT_LIMIT

    if requested_limit not in RECENT_REPORT_LIMIT_OPTIONS:
        requested_limit = DEFAULT_RECENT_REPORT_LIMIT

    effective_recent_limit = min(requested_limit, REPORT_RETENTION_LIMIT)

    return render_template(
        "result.html",
        output_file=None,
        config_file=None,
        recent_report_config_pairs=list_recent_report_config_pairs(limit=effective_recent_limit),
        recent_reports_limit=effective_recent_limit,
    )


@web.get("/download")
def download_report() -> Any:
    file_param = request.args.get("file", "")

    try:
        target = resolve_output_download_path(file_param)
    except (ValueError, FileNotFoundError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.index"))

    return send_file(target, as_attachment=True, download_name=target.name, mimetype="text/csv")


@web.get("/download-config")
def download_config() -> Any:
    file_param = request.args.get("file", "")

    try:
        target = resolve_config_download_path(file_param)
    except (ValueError, FileNotFoundError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.index"))

    return send_file(target, as_attachment=True, download_name=target.name, mimetype="application/json")
