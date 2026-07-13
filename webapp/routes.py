from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from .constants import DATASET_DEFAULT_COLUMNS, DATASET_OPTIONS, PROJECT_ROOT
from .form_config import build_config
from .services import (
    REPORT_RETENTION_LIMIT,
    list_recent_report_jobs,
    resolve_config_download_path,
    resolve_output_download_payload,
    save_generated_config,
    submit_report_job,
)

web = Blueprint("web", __name__)
_BASE_RECENT_REPORT_LIMIT_OPTIONS = (5, 10, 15, 20, 50)
RECENT_REPORT_LIMIT_OPTIONS = tuple(
    option for option in _BASE_RECENT_REPORT_LIMIT_OPTIONS if option <= REPORT_RETENTION_LIMIT
) or (REPORT_RETENTION_LIMIT,)
DEFAULT_RECENT_REPORT_LIMIT = REPORT_RETENTION_LIMIT


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
        job_id = submit_report_job(config_path)
    except Exception as exc:  # noqa: BLE001
        flash(f"Failed to submit report job: {exc}", "error")
        return redirect(url_for("web.index"))

    flash(f"Report job queued successfully. Job ID: {job_id}", "success")
    return redirect(url_for("web.results_page", limit=effective_recent_limit, submitted=job_id))


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
    submitted_job_id = request.args.get("submitted", "").strip()

    return render_template(
        "result.html",
        output_file=None,
        output_public_url="",
        config_file=None,
        recent_report_jobs=list_recent_report_jobs(limit=effective_recent_limit),
        submitted_job_id=submitted_job_id,
        recent_reports_limit=effective_recent_limit,
    )


@web.get("/download")
def download_report() -> Any:
    file_param = request.args.get("file", "")

    try:
        target, download_name = resolve_output_download_payload(file_param)
    except (ValueError, FileNotFoundError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.index"))

    return send_file(target, as_attachment=True, download_name=download_name, mimetype="text/csv")


@web.get("/download-config")
def download_config() -> Any:
    file_param = request.args.get("file", "")

    try:
        target = resolve_config_download_path(file_param)
    except (ValueError, FileNotFoundError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.index"))

    return send_file(target, as_attachment=True, download_name=target.name, mimetype="application/json")
