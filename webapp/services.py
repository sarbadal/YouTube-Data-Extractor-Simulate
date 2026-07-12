from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from .constants import CONFIG_OUTPUT_DIR, PROJECT_ROOT, SRC_PATH

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from youtube_extractor.extractors import run_extraction
from youtube_extractor.extractors.youtube_ads_extractor import DATASET_TO_FILE
from youtube_extractor.models import load_config

REPORT_RETENTION_LIMIT = 5


def _is_gcs_data_mode() -> bool:
    """Resolve whether storage should run in GCS mode.

    Why: the app supports both local development and cloud-backed operation.
    This helper centralizes mode selection so every call path uses the same
    rule and production cannot silently fall back to local disk.
    """
    mode = os.getenv("DATA_STORAGE_MODE", "local").strip().lower()
    env_type = os.getenv("ENV_TYPE", "dev").strip().lower()
    bucket_name = os.getenv("GCS_DATA_BUCKET", "").strip()

    if mode == "gcs":
        if not bucket_name:
            raise RuntimeError("GCS_DATA_BUCKET must be set when DATA_STORAGE_MODE=gcs")
        return True

    if bucket_name:
        return True

    if env_type == "prod":
        raise RuntimeError(
            "Production requires GCS-backed storage. Set DATA_STORAGE_MODE=gcs and GCS_DATA_BUCKET."
        )

    return False


def _get_gcs_client():
    """Create a Google Cloud Storage client when GCS mode is enabled.

    Why: importing cloud dependencies lazily avoids requiring the package in
    purely local runs while still failing with a clear message in GCS mode.
    """
    try:
        from google.cloud import storage
    except ImportError as exc:  # pragma: no cover - import guard for local-only runs
        raise RuntimeError("google-cloud-storage is required when DATA_STORAGE_MODE=gcs") from exc
    return storage.Client()


def _get_gcs_bucket_name() -> str:
    """Return the configured data bucket name.

    Why: many helpers need the same bucket and this check ensures configuration
    errors surface early with one consistent exception message.
    """
    bucket_name = os.getenv("GCS_DATA_BUCKET", "").strip()
    if not bucket_name:
        raise RuntimeError("GCS_DATA_BUCKET must be set when DATA_STORAGE_MODE=gcs")
    return bucket_name


def _get_gcs_output_prefix() -> str:
    """Return normalized GCS output prefix for generated reports.

    Why: normalizing leading/trailing slashes prevents malformed object names
    and keeps all output paths consistent across uploads and listings.
    """
    return os.getenv("GCS_OUTPUT_PREFIX", "outputs").strip().strip("/")


def _build_public_gcs_url(bucket_name: str, blob_name: str) -> str:
    """Build a direct public URL for a GCS object.

    Why: the UI uses this value to provide one-click downloads that bypass app
    proxying when objects are publicly readable.
    """
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name.lstrip('/')}"


def _build_output_blob_name(file_name: str) -> str:
    """Build canonical object path for an uploaded report file.

    Why: report uploads and report listings must agree on the same prefix/name
    convention so generated files are discoverable later in the UI.
    """
    output_prefix = _get_gcs_output_prefix()
    return f"{output_prefix}/{file_name}".strip("/")


def upload_local_file_to_gcs(local_path: Path, bucket_name: str, blob_name: str, content_type: str) -> str:
    """Upload a local artifact to GCS and return its public URL.

    Why: report generation writes files locally first, then this helper handles
    transfer to durable cloud storage used by download links.
    """
    if not local_path.exists() or not local_path.is_file():
        raise FileNotFoundError(f"Local file does not exist: {local_path}")

    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path), content_type=content_type)
    return _build_public_gcs_url(bucket_name, blob_name)


def download_gcs_file_to_local(bucket_name: str, blob_name: str, local_path: Path) -> Path:
    """Download one GCS object to a local path and return that path.

    Why: extraction code reads local CSV templates, so in GCS mode we stage only
    the required source file to local disk before running extraction.
    """
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if not blob.exists(client=client):
        raise FileNotFoundError(f"GCS object does not exist: gs://{bucket_name}/{blob_name}")

    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_path))
    return local_path


def save_generated_config(config_payload: dict) -> Path:
    """Persist generated extraction config JSON under configs/generated.

    Why: configs are saved for traceability and for pairing each report with the
    exact input definition shown in the results table.
    """
    CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config_name = f"config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.json"
    config_path = CONFIG_OUTPUT_DIR / config_name
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    return config_path


def ensure_required_dataset_local(config_path: Path) -> None:
    """Stage the required dataset CSV from GCS into local data directory.

    Why: the extractor is intentionally local-file based. This helper bridges
    cloud storage and local processing by downloading just the dataset needed
    for the current config instead of syncing the entire bucket.
    """
    if not _is_gcs_data_mode():
        return

    config = load_config(config_path)
    dataset_file = DATASET_TO_FILE.get(config.dataset)
    if not dataset_file:
        raise ValueError(f"Unsupported dataset: {config.dataset}")

    bucket_name = _get_gcs_bucket_name()
    data_prefix = os.getenv("GCS_DATA_PREFIX", "data").strip().strip("/")
    blob_name = f"{data_prefix}/{dataset_file}".strip("/")
    local_data_path = PROJECT_ROOT / "data" / dataset_file

    download_gcs_file_to_local(
        bucket_name=bucket_name,
        blob_name=blob_name,
        local_path=local_data_path,
    )


def execute_extraction(config_path: Path) -> tuple[Path, str]:
    """Run extraction, optionally upload output to GCS, and return report refs.

    Why: this is the orchestration boundary between web routes and storage.
    It ensures input data is staged, extraction executes once, and output is
    published as a public URL in GCS mode for direct downloads.
    """
    ensure_required_dataset_local(config_path)
    output_path = run_extraction(config_path=config_path, project_root=PROJECT_ROOT)
    output_ref = output_path.relative_to(PROJECT_ROOT)

    if _is_gcs_data_mode():
        bucket_name = _get_gcs_bucket_name()
        blob_name = _build_output_blob_name(output_path.name)
        public_url = upload_local_file_to_gcs(
            local_path=output_path,
            bucket_name=bucket_name,
            blob_name=blob_name,
            content_type="text/csv",
        )

        # Keep container filesystem clean in GCS mode after upload.
        try:
            output_path.unlink()
        except OSError:
            pass

        return Path(blob_name), public_url

    return output_ref, ""


def resolve_output_download_payload(file_param: str) -> tuple[Path | BinaryIO, str]:
    """Resolve report download source for Flask send_file.

    Why: routes should not care whether data is local or cloud-backed. This
    helper validates path scope and returns a file-like object plus filename for
    a consistent response path.
    """
    if _is_gcs_data_mode():
        normalized = file_param.strip().lstrip("/")
        output_prefix = _get_gcs_output_prefix()
        required_prefix = f"{output_prefix}/"
        if not normalized.startswith(required_prefix):
            raise ValueError("Invalid download path")

        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blob = bucket.blob(normalized)
        if not blob.exists(client=client):
            raise FileNotFoundError("Requested file does not exist")

        payload = io.BytesIO(blob.download_as_bytes())
        payload.seek(0)
        return payload, Path(normalized).name

    target = (PROJECT_ROOT / file_param).resolve()
    outputs_root = (PROJECT_ROOT / "outputs").resolve()

    if not str(target).startswith(str(outputs_root)):
        raise ValueError("Invalid download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested file does not exist")

    return target, target.name


def resolve_config_download_path(file_param: str) -> Path:
    """Resolve and validate local config JSON download path.

    Why: config files are stored locally and this check prevents path traversal
    while ensuring only known generated configs can be served.
    """
    target = (PROJECT_ROOT / file_param).resolve()
    configs_root = CONFIG_OUTPUT_DIR.resolve()

    if not str(target).startswith(str(configs_root)):
        raise ValueError("Invalid config download path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested config file does not exist")

    return target


def list_reports_for_client(client_id: str) -> list[str]:
    """List report object paths for one client, newest first.

    Why: client-scoped listings support report history views and allow the app
    to work against either local outputs or GCS objects transparently.
    """
    if _is_gcs_data_mode():
        output_prefix = _get_gcs_output_prefix()
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blobs = sorted(
            bucket.list_blobs(prefix=f"{output_prefix}/report_{client_id}_"),
            key=lambda blob: blob.updated or datetime.min,
            reverse=True,
        )
        return [blob.name for blob in blobs if blob.name.endswith(".csv")]

    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    matches = sorted(
        outputs_root.glob(f"report_{client_id}_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [path.relative_to(PROJECT_ROOT).as_posix() for path in matches]


def list_all_reports() -> list[str]:
    """List all generated reports in storage backend, newest first.

    Why: retention pruning and the results page need one canonical source of
    report ordering independent of local or GCS storage mode.
    """
    if _is_gcs_data_mode():
        output_prefix = _get_gcs_output_prefix()
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        blobs = sorted(
            bucket.list_blobs(prefix=f"{output_prefix}/report_"),
            key=lambda blob: blob.updated or datetime.min,
            reverse=True,
        )
        return [blob.name for blob in blobs if blob.name.endswith(".csv")]

    outputs_root = PROJECT_ROOT / "outputs"
    if not outputs_root.exists():
        return []

    return [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in sorted(
            outputs_root.glob("report_*.csv"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    ]


def prune_old_reports(max_reports: int = REPORT_RETENTION_LIMIT) -> int:
    """Delete older generated report CSV files and keep only the newest max_reports.

    Returns the number of deleted files.
    """
    if max_reports < 1:
        return 0

    reports = list_all_reports()
    stale_reports = reports[max_reports:]

    if _is_gcs_data_mode():
        client = _get_gcs_client()
        bucket = client.bucket(_get_gcs_bucket_name())
        deleted = 0
        for blob_name in stale_reports:
            try:
                bucket.blob(blob_name).delete()
                deleted += 1
            except Exception:  # noqa: BLE001
                continue
        return deleted

    deleted = 0
    for report_ref in stale_reports:
        try:
            (PROJECT_ROOT / report_ref).unlink()
            deleted += 1
        except OSError:
            # Ignore file deletion failures so report generation flow does not fail.
            continue

    return deleted


def list_recent_report_config_pairs(limit: int = 20) -> list[dict[str, str]]:
    """Build recent report rows paired with best-matching config files.

    Why: the results UI requires friendly row data (name, download refs, public
    URL, config metadata) without embedding storage or filename parsing logic
    inside templates.
    """
    recent_reports = list_all_reports()[:limit]
    pairs: list[dict[str, str]] = []
    report_bucket = _get_gcs_bucket_name() if _is_gcs_data_mode() else ""

    for report_ref in recent_reports:
        report_name = Path(report_ref).name
        timestamp_match = re.search(r"_(\d{8}_\d{6})\.csv$", report_name)
        config_rel = ""

        if timestamp_match:
            timestamp_token = timestamp_match.group(1)
            config_matches = sorted(
                CONFIG_OUTPUT_DIR.glob(f"config_{timestamp_token}_*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if config_matches:
                config_rel = config_matches[0].relative_to(PROJECT_ROOT).as_posix()

        pairs.append(
            {
                "report_file": report_ref,
                "report_name": report_name,
                "report_public_url": _build_public_gcs_url(report_bucket, report_ref)
                if report_bucket
                else "",
                "config_file": config_rel,
                "config_name": Path(config_rel).name if config_rel else "",
            }
        )

    return pairs
