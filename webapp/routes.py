from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from .constants import DATASET_DEFAULT_COLUMNS, DATASET_OPTIONS, PROJECT_ROOT
from .form_config import build_config
from .services import (
    execute_extraction,
    resolve_config_download_path,
    resolve_output_download_path,
    save_generated_config,
)

web = Blueprint("web", __name__)


@web.get("/")
def index() -> str:
    return render_template(
        "index.html",
        dataset_options=DATASET_OPTIONS,
        dataset_default_columns=DATASET_DEFAULT_COLUMNS,
        today=datetime.utcnow().date().isoformat(),
    )


@web.post("/generate")
def generate_report() -> Any:
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

    output_relpath = output_path.relative_to(PROJECT_ROOT)
    return render_template(
        "result.html",
        output_file=output_relpath.as_posix(),
        config_file=config_path.relative_to(PROJECT_ROOT).as_posix(),
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
